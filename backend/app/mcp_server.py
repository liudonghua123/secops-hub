"""MCP Server (fastmcp, streamable HTTP) mounted at /mcp on the same port.

Exposes SecOps Hub data to external AI clients (Claude / Cursor / WorkBuddy...):
  - get_asset_profile(asset_name)   资产多维画像（借鉴 ARL-Next MCP 设计）
  - search_vulnerabilities(query)   漏洞库检索
  - latest_intel(limit)             最新威胁情报

Implemented with the FastMCP server bundled in the `mcp` SDK (no fastmcp dep).
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("secops-hub", streamable_http_path="/")


@mcp.tool()
def get_asset_profile(asset_name: str) -> str:
    """获取指定资产的多维画像：基本信息、指纹、匹配漏洞、风险评分。"""
    from .database import SessionLocal
    from .models import Asset, Vulnerability

    db = SessionLocal()
    try:
        a = db.query(Asset).filter(Asset.name.like(f"%{asset_name}%")).first()
        if not a:
            a = db.query(Asset).filter(Asset.value.like(f"%{asset_name}%")).first()
        if not a:
            return f"未找到资产：{asset_name}"
        kws = [k.strip().lower() for k in a.fingerprint.split(",") if k.strip()]
        matched = []
        for v in db.query(Vulnerability).all():
            vkws = [k.strip().lower() for k in v.affected_keywords.split(",") if k.strip()]
            if any(k in f"{a.name} {a.fingerprint}".lower() for k in vkws):
                matched.append(f"{v.title}（{v.severity}）")
        score = sum({"严重": 10, "高危": 7, "中危": 4, "低危": 1}.get(m.split("（")[1][:-1], 0) for m in matched)
        return (
            f"资产画像：{a.name}（{a.type}）\n值：{a.value}\n责任部门：{a.owner_dept}\n"
            f"关键性：{a.criticality}｜互联网暴露：{'是' if a.exposure else '否'}\n"
            f"备案号：{a.icp_no or '无'}\n指纹：{a.fingerprint or '无'}\n"
            f"匹配漏洞 {len(matched)} 项：{'；'.join(matched) if matched else '无'}\n"
            f"风险评分：{score}"
        )
    finally:
        db.close()


@mcp.tool()
def search_vulnerabilities(query: str) -> str:
    """按编号或关键词检索漏洞库。"""
    from .database import SessionLocal
    from .models import Vulnerability

    db = SessionLocal()
    try:
        like = f"%{query}%"
        items = db.query(Vulnerability).filter(
            Vulnerability.title.like(like) | Vulnerability.cve_id.like(like) |
            Vulnerability.cnvd_id.like(like) | Vulnerability.cnnvd_id.like(like)
        ).limit(10).all()
        if not items:
            return f"漏洞库中未检索到：{query}"
        return "\n".join(
            f"[{v.severity} CVSS {v.cvss}] {v.title} | CVE:{v.cve_id or '-'} CNVD:{v.cnvd_id or '-'} CNNVD:{v.cnnvd_id or '-'} | POC:{'有' if v.poc_available else '无'}"
            for v in items)
    finally:
        db.close()


@mcp.tool()
def latest_intel(limit: int = 5) -> str:
    """获取最新威胁情报条目。"""
    from .database import SessionLocal
    from .models import IntelItem

    db = SessionLocal()
    try:
        items = db.query(IntelItem).order_by(IntelItem.published_at.desc()).limit(limit).all()
        return "\n".join(f"[{i.source} {i.published_at}] {i.title}（{i.severity or '未评级'}）" for i in items)
    finally:
        db.close()
