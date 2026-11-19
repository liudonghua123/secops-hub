"""AgentScope runtime: build a ReActAgent from an AgentProfile and run a chat turn.

Composition per agent:
  model    -> OpenAI-compatible endpoint (env LLM_API_BASE/LLM_API_KEY, LLM_MODEL
              or agent.model_name), including local Ollama / vLLM
  skills   -> builtin skills register imported functions; custom/hub skills are
              exec'd (admin-only) and every `tool_*` function is registered
  mcp      -> stdio (StdIOStatefulClient, connect/close) and streamable-http
              (HttpStatelessClient) servers registered on the toolkit
  knowledge-> a per-agent kb_search tool restricted to the bound knowledge bases
  memory   -> session history loaded from DB into InMemoryMemory
"""
import json
import os

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg, TextBlock
from agentscope.model import OpenAIChatModel
from agentscope.mcp import HttpStatelessClient, StdIOStatefulClient
from agentscope.tool import Toolkit, ToolResponse

from .database import SessionLocal
from .kb_engine import search_kb
from .models import AgentProfile, KnowledgeDoc, MCPServer, SkillItem
from .skills_builtin import BUILTIN_SKILLS, BUILTIN_TOOLS

EXEC_GLOBALS = {"__builtins__": __builtins__, "json": json, "os": os}


def _wrap_tool(fn: callable) -> callable:
    """Wrap a plain function (returns str) into an async function that
    returns a ToolResponse — required by agentscope 1.x Toolkit."""
    import functools
    import inspect

    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def awrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            if isinstance(result, ToolResponse):
                return result
            return ToolResponse(content=[TextBlock(type="text", text=str(result))])
        return awrapper

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        if isinstance(result, ToolResponse):
            return result
        return ToolResponse(content=[TextBlock(type="text", text=str(result))])

    return wrapper


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
    toolkit = Toolkit()

    # --- skills ---
    skill_ids = json.loads(profile.skill_ids or "[]")
    db = SessionLocal()
    try:
        skills = db.query(SkillItem).filter(SkillItem.id.in_(skill_ids), SkillItem.enabled == True).all()  # noqa: E712
    finally:
        db.close()
    for s in skills:
        tools = _load_skill_tools(s)
        err = tools.pop("__error__", None)
        if err:
            meta["mcp_errors"].append(err)
        for name, fn in tools.items():
            try:
                toolkit.register_tool_function(_wrap_tool(fn))
                meta["tools"].append(name)
            except Exception as exc:
                meta["mcp_errors"].append(f"注册 {name} 失败: {exc}")

    # --- knowledge bases ---
    kb_ids = json.loads(profile.kb_ids or "[]")
    if kb_ids:
        try:
            toolkit.register_tool_function(_wrap_tool(_build_kb_tool(kb_ids)))
            meta["tools"].append("search_bound_knowledge")
        except Exception as exc:
            meta["mcp_errors"].append(f"注册知识库工具失败: {exc}")

    # --- mcp servers ---
    mcp_ids = json.loads(profile.mcp_ids or "[]")
    stdio_clients: list = []
    db = SessionLocal()
    try:
        servers = db.query(MCPServer).filter(MCPServer.id.in_(mcp_ids), MCPServer.enabled == True).all()  # noqa: E712
    finally:
        db.close()
    for srv in servers:
        try:
            if srv.transport == "stdio":
                client = StdIOStatefulClient(
                    name=srv.name, command=srv.command,
                    args=json.loads(srv.args or "[]"),
                )
                await client.connect()
                stdio_clients.append(client)
            else:
                client = HttpStatelessClient(
                    name=srv.name, transport="streamable_http", url=srv.url,
                    headers=json.loads(srv.headers or "{}"),
                )
            await toolkit.register_mcp_client(client)
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
        model_name=model_name, api_key=key, stream=True,
        client_kwargs={"base_url": base.rstrip("/")},
    )

    # --- memory: session history ---
    memory = InMemoryMemory()
    for m in history:
        await memory.add(m)

    agent = ReActAgent(
        name=profile.name or "secops-agent",
        sys_prompt=(profile.sys_prompt or "你是单位网络安全值守助手。")
        + "\n\n【输出规范】\n"
        "1. 最终回复只输出给用户的正式答案正文，不要包含任何内部思考过程、"
        "推理草稿或类似\"我先来分析\"的过渡语开头。\n"
        "2. 回答使用简体中文，用 Markdown 组织（标题、表格、列表），"
        "专业术语保留英文原名。\n"
        "3. 涉及数据时优先调用工具查询真实数据，不要编造；工具结果"
        "中没有的信息要明确说明\"暂无数据\"。\n"
        "4. 给出处置建议时注明优先级（P0/P1/P2）与建议时限。",
        model=model,
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=memory,
        max_iters=profile.max_iters or 10,
    )

    async def cleanup():
        for c in stdio_clients:
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
        role = "assistant" if row["role"] == "assistant" else "user"
        if row["role"] not in ("user", "assistant"):
            continue
        history.append(Msg(profile.name or "agent", row["content"], role))
    agent, cleanup, meta = await build_agent(profile, history)
    try:
        reply = await agent(Msg(profile.name or "agent", user_text, "user"))
        text = reply.get_text_content() if reply else ""
        # reasoning models may inline think blocks in the final text
        from .ai_service import strip_reasoning
        text = strip_reasoning(text or "")
        meta["usage"] = str(getattr(reply, "usage_metadata", "") or "")
        return {"answer": text, "meta": meta}
    finally:
        await cleanup()
