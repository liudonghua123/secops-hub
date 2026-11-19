"""CNVD / CNNVD importers.

Both databases have NO open public API:
  - CNVD (cnvd.org.cn): batch XML/JSON downloads require a registered unit account.
  - CNNVD (cnnvd.org.cn): API access requires official authorization (level-1/2 users).

Workflow for a unit: obtain the account, export the incremental vulnerability
file (XML/JSON) from the portal, then POST it to /api/sync/import as JSON.
The importer validates and deduplicates; unknown fields are ignored.

Expected JSON: a list of records or {"records": [...]}, each record supports:
  cve_id / cnvd_id / cnnvd_id, title, severity (严重|高危|中危|低危 or CVSS number),
  cvss (number, optional — used when severity is numeric), description,
  affected_keywords, poc_available, fix_suggestion, published_at
"""
import json

from sqlalchemy.orm import Session

from .common import cvss_to_severity, upsert_vulnerability

VALID_SEV = {"严重", "高危", "中危", "低危"}


def _normalize(rec: dict, default_source: str) -> dict | None:
    vid = rec.get("cnvd_id") or rec.get("cnnvd_id") or rec.get("cve_id")
    if not vid:
        return None
    sev = rec.get("severity") or ""
    cvss = rec.get("cvss")
    if sev not in VALID_SEV:
        try:
            sev = cvss_to_severity(float(sev or cvss or 0))
        except (TypeError, ValueError):
            sev = "中危"
    return {
        "cve_id": rec.get("cve_id") or "",
        "cnvd_id": rec.get("cnvd_id") or "",
        "cnnvd_id": rec.get("cnnvd_id") or "",
        "title": str(rec.get("title") or vid)[:300],
        "severity": sev,
        "cvss": float(cvss or 0.0),
        "source": rec.get("source") or default_source,
        "description": str(rec.get("description") or "")[:2000],
        "affected_keywords": str(rec.get("affected_keywords") or "")[:500],
        "poc_available": bool(rec.get("poc_available", False)),
        "fix_suggestion": str(rec.get("fix_suggestion") or "")[:1000],
        "published_at": str(rec.get("published_at") or "")[:10],
    }


def import_cnvd(db: Session, raw: str | list | dict) -> dict:
    """Import CNVD batch data from JSON text, list, or dict."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"invalid JSON: {exc}"}
    records = raw.get("records") if isinstance(raw, dict) else raw
    if not isinstance(records, list):
        return {"ok": False, "error": "expected a list or {\"records\": [...]}"}

    stats = {"add": 0, "update": 0, "same": 0, "skip": 0}
    for rec in records:
        norm = _normalize(rec, "CNVD")
        if not norm:
            stats["skip"] += 1
            continue
        stats[upsert_vulnerability(db, norm)] += 1
    db.commit()
    return {"ok": True, "source": "CNVD import", "received": len(records), **stats}
