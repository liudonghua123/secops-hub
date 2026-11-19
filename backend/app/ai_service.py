"""AI service layer.

Pluggable LLM: any OpenAI-compatible endpoint via env vars
  LLM_API_BASE / LLM_API_KEY / LLM_MODEL
Fallback: deterministic rule-based analysis (no key required),
borrowed from CyberSecurity-Intelligence-Platform's degrade strategy.
"""
import os
import re

import httpx


OPEN = '<think>'
CLOSE = '</think>'


def strip_reasoning(text: str) -> str:
    """Strip inline chain-of-thought that some reasoning models (MiniMax,
    DeepSeek-R1 etc. via OpenAI-compatible gateways) emit as <think>...</think>
    blocks inside the message content.

    Handles both closed pairs and unclosed open tags (gateway may
    swallow the close tag): in the latter case cut at the first
    "answer boundary" (blank line followed by a heading / list /
    table / quote marker) instead of swallowing the entire answer.
    """
    if not text or OPEN not in text:
        return text
    # 1) closed pairs
    text = re.sub(
        re.escape(OPEN) + r".*?" + re.escape(CLOSE) + r"\s*",
        "", text, flags=re.S)
    # 2) unclosed open tag: cut at first answer boundary
    if OPEN in text:
        text = re.sub(
            re.escape(OPEN) + r".*?(?=\n\n\n|\n\n[#>*\-`]|\Z)",
            "", text, flags=re.S)
    # 3) last resort: keep only the last non-empty paragraph
    if OPEN in text:
        tail = text.split(OPEN, 1)[1]
        segs = [s for s in re.split(r"\n{2,}", tail) if s.strip()]
        text = segs[-1] if segs else tail
    return text.strip()


RULE_SEVERITY_ACTION = {
    "严重": "立即处置（24 小时内）：确认受影响资产 → 隔离或临时缓解 → 升级补丁 → 复测验证",
    "高危": "优先处置（72 小时内）：核实受影响范围 → 安排补丁或规则缓解 → 复测",
    "中危": "常规处置（7 个工作日内）：纳入补丁计划，加强访问控制",
    "低危": "计划处置：纳入周期加固清单",
}


def llm_available() -> bool:
    return bool(os.environ.get("LLM_API_BASE") and os.environ.get("LLM_API_KEY"))


def llm_chat(messages: list[dict], max_tokens: int = 2000) -> str | None:
    base = os.environ.get("LLM_API_BASE", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": messages,
                  "temperature": 0.3, "max_tokens": max_tokens},
            timeout=120,
        )
        resp.raise_for_status()
        return strip_reasoning(resp.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


def vuln_brief_rule_based(v) -> str:
    """Rule-based vulnerability briefing (fallback)."""
    matched = v.get("matched_assets", [])
    lines = [
        f"【漏洞研判简报】{v['title']}",
        f"编号：{v.get('cve_id') or v.get('cnvd_id') or v.get('cnnvd_id') or '内部'}　级别：{v['severity']}（CVSS {v.get('cvss', 0)}）",
        f"披露时间：{v.get('published_at', '未知')}　来源：{v.get('source', '')}",
        "",
        f"1. 漏洞概况：{v.get('description', '')}",
        "",
        f"2. 利用态势：POC {'已有公开' if v.get('poc_available') else '暂未见公开'}；"
        f"在野利用{'已出现，风险等级上调' if v.get('exploited_in_wild') else '暂未观察到'}。",
        "",
        f"3. 资产影响：经指纹匹配，本单位共 {len(matched)} 项资产受影响"
        + (f"：{'; '.join(a['name'] + '(' + a['owner_dept'] + ')' for a in matched[:5])}" if matched else "（建议扩大指纹匹配范围）"),
        "",
        f"4. 处置建议：{v.get('fix_suggestion', RULE_SEVERITY_ACTION.get(v['severity'], '按常规流程处置'))}",
        f"5. 处置时限：{RULE_SEVERITY_ACTION.get(v['severity'], '')}",
        "",
        "（本简报由规则引擎生成，处置动作请经人工确认后执行）",
    ]
    return "\n".join(lines)


def vuln_brief(v) -> str:
    """AI vulnerability briefing: LLM when configured, rule engine otherwise."""
    if not llm_available():
        return vuln_brief_rule_based(v)
    context = (
        f"漏洞标题: {v['title']}\n级别: {v['severity']} CVSS: {v['cvss']}\n"
        f"描述: {v.get('description','')}\nPOC公开: {v.get('poc_available')}\n"
        f"在野利用: {v.get('exploited_in_wild')}\n"
        f"受影响资产: {[a['name'] for a in v.get('matched_assets', [])]}\n"
        f"修复建议: {v.get('fix_suggestion','')}"
    )
    messages = [
        {"role": "system", "content": "你是单位网络安全值守助手。基于给定信息生成简洁的漏洞研判简报，包含：漏洞概况、利用态势、资产影响、处置建议与时限。输出中文，条理清晰，不超过 400 字。"},
        {"role": "user", "content": context},
    ]
    result = llm_chat(messages)
    return result if result else vuln_brief_rule_based(v)


def answer_rule_based(question: str) -> str:
    q = question.lower()
    hints = [
        "当前为规则引擎应答（未配置 LLM_API_BASE/LLM_API_KEY，可接入任意 OpenAI 兼容接口或本地 Ollama）。",
        "可尝试的问题：某漏洞影响哪些资产、扫描任务如何复核误报、最新情报里有哪些高危预警。",
    ]
    if any(k in q for k in ["资产", "暴露面"]):
        return "资产维度请查看「资产管理」模块：支持按关键性/暴露面/部门筛选，资产详情页提供指纹、匹配漏洞与风险评分画像。" + " / ".join(hints[:1])
    if any(k in q for k in ["误报", "复核", "验证"]):
        return "扫描发现需人工复核：在「扫描任务」中打开任务详情，对每条发现可执行「确认漏洞」或「标记误报」，复核记录会留存审计。" + " / ".join(hints[:1])
    return "我是单位安全值守助手（规则引擎模式）。问题涉及具体数据时，建议先在对应模块检索；如需自然语言研判，请配置 LLM 接口。"
