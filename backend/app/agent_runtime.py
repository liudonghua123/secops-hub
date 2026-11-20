"""AgentScope runtime: build an Agent (v2) from an AgentProfile and run a chat turn.

Composition per agent (agentscope >= 2.0):
  model    -> OpenAI-compatible endpoint (env LLM_API_BASE/LLM_API_KEY, LLM_MODEL
              or agent.model_name), including local Ollama / vLLM
  skills   -> builtin skills register imported functions; custom/hub skills are
              exec'd (admin-only) and every `tool_*` function is registered
              as a FunctionTool with explicit ALLOW permission (server-side,
              read-only queries — no human-in-the-loop needed)
  mcp      -> stdio (stateful, connect/close) and streamable-http (stateless)
              servers registered on the toolkit via MCPClient
  knowledge-> a per-agent kb_search tool restricted to the bound knowledge bases
  memory   -> session history loaded from DB into AgentState.context
"""
import functools
import inspect
import json
import os

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import OpenAICredential
from agentscope.message import AssistantMsg, Msg, TextBlock, UserMsg
from agentscope.model import OpenAIChatModel
from agentscope.mcp import HttpMCPConfig, MCPClient, StdioMCPConfig
from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.tool import FunctionTool, MCPTool, Toolkit

from .database import SessionLocal
from .kb_engine import search_kb
from .models import AgentProfile, KnowledgeDoc, MCPServer, SkillItem
from .skills_builtin import BUILTIN_SKILLS, BUILTIN_TOOLS

EXEC_GLOBALS = {"__builtins__": __builtins__, "json": json, "os": os}

_ALLOW = PermissionDecision(
    behavior=PermissionBehavior.ALLOW,
    message="Internal read-only query tool, auto-allowed.",
)


class _ReadOnlyMCPClient(MCPClient):
    """MCPClient whose tools are treated as read-only.

    The platform MCP servers expose only read-only query tools, so the
    v2 permission engine should auto-allow them instead of parking the
    reply on RequireUserConfirmEvent (MCPTool.check_permissions honors
    ``is_read_only``).
    """

    async def get_tool(self, name: str) -> MCPTool:  # type: ignore[override]
        tool = await super().get_tool(name)
        try:
            tool.is_read_only = True
        except Exception:
            pass
        return tool


def _wrap_tool(fn: callable) -> FunctionTool:
    """Wrap a plain function (returns str / dict) into a v2 FunctionTool
    with explicit ALLOW permission (unattended server-side use)."""
    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def awrapper(*args, **kwargs):
            return await fn(*args, **kwargs)
        target = awrapper
    else:
        target = fn
    return FunctionTool(target, permission=_ALLOW)


def llm_configured() -> bool:
    return bool(os.environ.get("LLM_API_BASE") and os.environ.get("LLM_API_KEY"))


def _load_skill_tools(skill: SkillItem) -> dict[str, callable]:
    """Resolve a skill row to {tool_name: function}."""
    if skill.source == "builtin":
        catalog = next((s for s in BUILTIN_SKILLS if s["name"] == skill.name), None)
        if not catalog:
            return {}
        return {t: BUILTIN_TOOLS[t] for t in catalog.get("tools", []) if t in BUILTIN_TOOLS}
    # custom / hub: exec code, register functions named tool_*
    funcs: dict[str, callable] = {}
    try:
        ns: dict = dict(EXEC_GLOBALS)
        exec(skill.code, ns)  # noqa: S102 - admin-provided skill packs only
        for k, v in ns.items():
            if k.startswith("tool_") and callable(v) and getattr(v, "__module__", "") != "builtins":
                funcs[k] = v
    except Exception as exc:
        funcs["__error__"] = f"skill {skill.name} 加载失败: {exc}"
    return funcs


def _build_kb_tool(kb_ids: list[int]):
    def search_bound_knowledge(query: str) -> str:
        """在本 agent 绑定的知识库中检索资料片段（预案、制度、设备资料等）。

        Args:
            query (str): 检索问题或关键词。
        """
        db = SessionLocal()
        docs = []
        try:
            for kid in kb_ids:
                for doc in db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kid).all():
                    docs.append(doc)
        finally:
            db.close()
        if not docs:
            return "[]"
        from .kb_engine import _score
        import re as _re

        terms = [t for t in _re.split(r"[\s,，。;；?？]+", query or "") if t]
        hits = []
        for doc in docs:
            try:
                chunks = json.loads(doc.chunks or "[]")
            except json.JSONDecodeError:
                continue
            for ch in chunks:
                s = _score(ch, terms)
                if s > 0:
                    hits.append({"score": s, "doc": doc.filename, "text": ch[:400]})
        hits.sort(key=lambda h: -h["score"])
        return json.dumps(hits[:5], ensure_ascii=False)

    return search_bound_knowledge


async def build_agent(profile: AgentProfile, history: list[Msg]) -> tuple:
    """Build (agent, cleanup, meta). Caller must await cleanup() after the turn."""
    meta: dict = {"tools": [], "mcp_errors": [], "model": ""}
    tools: list[FunctionTool] = []

    # --- skills ---
    skill_ids = json.loads(profile.skill_ids or "[]")
    db = SessionLocal()
    try:
        skills = db.query(SkillItem).filter(SkillItem.id.in_(skill_ids), SkillItem.enabled == True).all()  # noqa: E712
    finally:
        db.close()
    for s in skills:
        fns = _load_skill_tools(s)
        err = fns.pop("__error__", None)
        if err:
            meta["mcp_errors"].append(err)
        for name, fn in fns.items():
            try:
                tools.append(_wrap_tool(fn))
                meta["tools"].append(name)
            except Exception as exc:
                meta["mcp_errors"].append(f"注册 {name} 失败: {exc}")

    # --- knowledge bases ---
    kb_ids = json.loads(profile.kb_ids or "[]")
    if kb_ids:
        try:
            tools.append(_wrap_tool(_build_kb_tool(kb_ids)))
            meta["tools"].append("search_bound_knowledge")
        except Exception as exc:
            meta["mcp_errors"].append(f"注册知识库工具失败: {exc}")

    # --- mcp servers ---
    mcp_ids = json.loads(profile.mcp_ids or "[]")
    stateful_clients: list[MCPClient] = []
    mcp_clients: list[MCPClient] = []
    db = SessionLocal()
    try:
        servers = db.query(MCPServer).filter(MCPServer.id.in_(mcp_ids), MCPServer.enabled == True).all()  # noqa: E712
    finally:
        db.close()
    for srv in servers:
        try:
            if srv.transport == "stdio":
                client = _ReadOnlyMCPClient(
                    name=srv.name,
                    is_stateful=True,
                    mcp_config=StdioMCPConfig(
                        command=srv.command,
                        args=json.loads(srv.args or "[]"),
                    ),
                )
                await client.connect()
                stateful_clients.append(client)
            else:
                client = _ReadOnlyMCPClient(
                    name=srv.name,
                    is_stateful=False,
                    mcp_config=HttpMCPConfig(
                        url=srv.url,
                        headers=json.loads(srv.headers or "{}"),
                    ),
                )
            mcp_clients.append(client)
            # Platform MCP servers expose read-only query tools; mark
            # them read-only so the v2 permission engine auto-allows
            # instead of parking the reply on RequireUserConfirmEvent.
            # MCPClient is a pydantic model — patch get_tool's product
            # via subclass-free wrapper on list_tools using object attr.
            _orig_get_tool = MCPClient.get_tool.__get__(client)

            async def _get_tool_readonly(name, _orig=_orig_get_tool):
                tool_ = await _orig(name)
                try:
                    tool_.is_read_only = True
                except Exception:
                    pass
                return tool_

            try:
                client.get_tool = _get_tool_readonly  # type: ignore[method-assign]
            except Exception:
                pass  # pydantic may forbid attr assignment; tools then ASK
            try:
                tool_schemas = await client.list_tools()
                srv_tools = [t.name for t in (tool_schemas or [])]
            except Exception:
                srv_tools = []
            meta["tools"].extend(srv_tools)
            meta["mcp_ok"] = meta.get("mcp_ok", []) + [srv.name]
        except Exception as exc:
            msg = str(exc)
            if "already registered" in msg:
                dup = msg.split("'")[1] if "'" in msg else ""
                meta["mcp_errors"].append(
                    f"MCP {srv.name} 跳过：工具 {dup} 与已注册技能重名（同功能重复绑定，不影响使用）")
            else:
                meta["mcp_errors"].append(f"MCP {srv.name} 连接失败: {msg[:200]}")

    # --- model ---
    base = os.environ.get("LLM_API_BASE", "")
    key = os.environ.get("LLM_API_KEY", "")
    model_name = profile.model_name or os.environ.get("LLM_MODEL", "gpt-4o-mini")
    meta["model"] = model_name
    model = OpenAIChatModel(
        credential=OpenAICredential(api_key=key, base_url=base.rstrip("/") or None),
        model=model_name,
        stream=True,
        parameters=OpenAIChatModel.Parameters(max_tokens=2000),
        client_kwargs={"timeout": 120},
    )

    toolkit = Toolkit(tools=tools, mcps=mcp_clients)

    # --- state: seed session history ---
    agent = Agent(
        name=profile.name or "secops-agent",
        system_prompt=(profile.sys_prompt or "你是单位网络安全值守助手。")
        + "\n\n【输出规范】\n"
        "1. 最终回复只输出给用户的正式答案正文，不要包含任何内部思考过程、"
        "推理草稿或类似\"我先来分析\"的过渡语开头。\n"
        "2. 回答使用简体中文，用 Markdown 组织（标题、表格、列表），"
        "专业术语保留英文原名。\n"
        "3. 涉及数据时优先调用工具查询真实数据，不要编造；工具结果"
        "中没有的信息要明确说明\"暂无数据\"。\n"
        "4. 给出处置建议时注明优先级（P0/P1/P2）与建议时限。",
        model=model,
        toolkit=toolkit,
        react_config=ReActConfig(max_iters=profile.max_iters or 10),
    )
    if history:
        try:
            r = agent.observe(history)
            if inspect.iscoroutine(r):
                await r
        except Exception:
            pass  # history seeding is best-effort

    async def cleanup():
        for c in stateful_clients:
            try:
                await c.close()
            except Exception:
                pass

    return agent, cleanup, meta


async def run_chat_turn(profile: AgentProfile, history_rows: list[dict],
                        user_text: str) -> dict:
    """Run one chat turn. Returns {answer, meta}. Raises when LLM unconfigured."""
    if not llm_configured():
        raise RuntimeError("LLM_UNCONFIGURED")
    history = []
    for row in history_rows:
        if row["role"] not in ("user", "assistant"):
            continue
        if row["role"] == "assistant":
            history.append(AssistantMsg(profile.name or "agent", row["content"]))
        else:
            history.append(UserMsg(profile.name or "agent", row["content"]))
    agent, cleanup, meta = await build_agent(profile, history)
    try:
        reply = await agent.reply(UserMsg(profile.name or "agent", user_text))
        text = reply.get_text_content() if reply else ""
        # reasoning models may inline think blocks in the final text
        from .ai_service import strip_reasoning
        text = strip_reasoning(text or "")
        meta["usage"] = str(getattr(reply, "usage", "") or "")
        return {"answer": text, "meta": meta}
    finally:
        await cleanup()
