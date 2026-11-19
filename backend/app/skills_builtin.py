"""Built-in skills: tool packs that can be bound to agents.

A skill is python code defining functions with type hints + docstrings.
For builtin skills the functions are imported directly (safe); for
custom/hub skills the code is exec'd in a restricted namespace (admin-only).

`sync_builtin_skills()` upserts the builtin catalog into the skills table.
"""
import json

from .database import SessionLocal
from .models import SkillItem

# ---------------------------------------------------------------- tool functions


def get_assets(keyword: str = "") -> str:
    """查询单位资产清单。可按关键词过滤名称/值/部门。

    Args:
        keyword (str): 关键词，留空返回全部资产（最多 50 条）。
    """
    from .database import SessionLocal as _SL
    from .models import Asset

    db = _SL()
    try:
        q = db.query(Asset)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(Asset.name.like(like) | Asset.value.like(like) | Asset.owner_dept.like(like))
        items = q.limit(50).all()
        return json.dumps([{
            "id": a.id, "name": a.name, "type": a.type, "value": a.value,
            "dept": a.owner_dept, "criticality": a.criticality,
            "exposure": a.exposure, "fingerprint": a.fingerprint,
        } for a in items], ensure_ascii=False)
    finally:
        db.close()


def search_vulns(keyword: str = "", severity: str = "") -> str:
    """检索漏洞库（CVE/CNVD/CNNVD）。返回编号、级别、CVSS、POC 与受影响资产。

    Args:
        keyword (str): 漏洞名称或编号关键词。
        severity (str): 级别过滤：严重/高危/中危/低危，留空不过滤。
    """
    from .database import SessionLocal as _SL
    from .models import Asset, Vulnerability

    db = _SL()
    try:
        q = db.query(Vulnerability)
        if keyword:
            like = f"%{keyword}%"
            q = q.filter(Vulnerability.title.like(like) | Vulnerability.cve_id.like(like)
                         | Vulnerability.cnvd_id.like(like) | Vulnerability.cnnvd_id.like(like))
        if severity:
            q = q.filter(Vulnerability.severity == severity)
        out = []
        for v in q.limit(20).all():
            kws = [k.strip().lower() for k in v.affected_keywords.split(",") if k.strip()]
            matched = [a.name for a in db.query(Asset).all()
                       if any(k in f"{a.name} {a.fingerprint}".lower() for k in kws)]
            out.append({
                "id": v.id, "title": v.title, "severity": v.severity, "cvss": v.cvss,
                "cve": v.cve_id, "cnvd": v.cnvd_id, "cnnvd": v.cnnvd_id,
                "poc": v.poc_available, "matched_assets": matched,
            })
        return json.dumps(out, ensure_ascii=False)
    finally:
        db.close()


def latest_intel(limit: int = 8) -> str:
    """获取最新威胁情报条目（多源聚合）。

    Args:
        limit (int): 返回条数，默认 8，最大 20。
    """
    from .database import SessionLocal as _SL
    from .models import IntelItem

    db = _SL()
    try:
        items = db.query(IntelItem).order_by(IntelItem.published_at.desc()).limit(min(limit, 20)).all()
        return json.dumps([{
            "source": i.source, "title": i.title, "severity": i.severity,
            "ref": i.ref_id, "date": i.published_at,
        } for i in items], ensure_ascii=False)
    finally:
        db.close()


def trigger_nvd_sync() -> str:
    """触发一次 NVD 增量同步（最近 1 天，最多 50 条）。用于值守时刷新漏洞情报。"""
    from .fetchers.nvd import sync_nvd
    db = SessionLocal()
    try:
        return json.dumps(sync_nvd(db, days=1, max_results=50), ensure_ascii=False)
    finally:
        db.close()


def kb_search(query: str, kb_name: str = "") -> str:
    """在知识库中检索资料片段。绑定知识库的 agent 会自动获得本工具。

    Args:
        query (str): 检索问题或关键词。
        kb_name (str): 知识库名称，留空检索全部知识库。
    """
    from .kb_engine import search_kb
    return json.dumps(search_kb(query, kb_name), ensure_ascii=False)


BUILTIN_TOOLS = {
    "get_assets": get_assets,
    "search_vulns": search_vulns,
    "latest_intel": latest_intel,
    "trigger_nvd_sync": trigger_nvd_sync,
    "kb_search": kb_search,
}

BUILTIN_SKILLS = [
    {
        "name": "secops-core",
        "version": "1.1.0",
        "description": "平台核心查询：资产清单、漏洞检索、最新威胁情报",
        "tools": ["get_assets", "search_vulns", "latest_intel"],
        "code": "",  # builtin skills register imported functions directly
    },
    {
        "name": "intel-ops",
        "version": "1.0.0",
        "description": "情报运营：触发 NVD 增量同步，用于值守刷新",
        "tools": ["trigger_nvd_sync"],
        "code": "",
    },
    {
        "name": "kb-search",
        "version": "1.0.0",
        "description": "知识库检索：在绑定知识库的资料中查找片段",
        "tools": ["kb_search"],
        "code": "",
    },
]


def sync_builtin_skills():
    """Upsert builtin skill catalog into DB (keeps versions fresh)."""
    db = SessionLocal()
    try:
        for s in BUILTIN_SKILLS:
            row = db.query(SkillItem).filter(SkillItem.name == s["name"]).first()
            if row:
                row.version = s["version"]
                row.description = s["description"]
            else:
                db.add(SkillItem(name=s["name"], version=s["version"],
                                 source="builtin", description=s["description"], code=""))
        db.commit()
    finally:
        db.close()
