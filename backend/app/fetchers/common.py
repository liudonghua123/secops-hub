"""Shared helpers for vulnerability fetchers."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models import IntelItem, Vulnerability


def _maybe_alert(db: Session, vuln: Vulnerability, is_new: bool):
    """Auto alert for critical/high vulns (dedup handled by push_alert)."""
    if vuln.severity not in ("严重", "高危"):
        return
    try:
        from ..routers.alerts import push_alert
        push_alert(db, vuln.severity,
                   f"【{vuln.severity}】{vuln.title}",
                   f"CVSS {vuln.cvss}｜POC：{'有' if vuln.poc_available else '无'}｜在野利用：{'是' if vuln.exploited_in_wild else '否'}",
                   ref_type="vuln", ref_id=vuln.id)
    except Exception:
        pass


def cvss_to_severity(score: float) -> str:
    if score >= 9.0:
        return "严重"
    if score >= 7.0:
        return "高危"
    if score >= 4.0:
        return "中危"
    return "低危"


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000")


def upsert_vulnerability(db: Session, data: dict) -> str:
    """Insert or update a vulnerability by its primary id. Returns action."""
    vid = data.get("cve_id") or data.get("cnvd_id") or data.get("cnnvd_id")
    if not vid:
        return "skip"
    existing = None
    if data.get("cve_id"):
        existing = db.query(Vulnerability).filter(Vulnerability.cve_id == data["cve_id"]).first()
    if not existing and data.get("cnvd_id"):
        existing = db.query(Vulnerability).filter(Vulnerability.cnvd_id == data["cnvd_id"]).first()
    if not existing and data.get("cnnvd_id"):
        existing = db.query(Vulnerability).filter(Vulnerability.cnnvd_id == data["cnnvd_id"]).first()
    if existing:
        changed = False
        for k in ("title", "description", "cvss", "severity", "poc_available", "exploited_in_wild"):
            new = data.get(k)
            if new is not None and getattr(existing, k) != new:
                setattr(existing, k, new)
                changed = True
        new_kw = (data.get("affected_keywords") or "").strip()
        if new_kw and getattr(existing, "affected_keywords", "") != new_kw:
            setattr(existing, "affected_keywords", new_kw)
            changed = True
        return "update" if changed else "same"
    db.add(Vulnerability(**data))
    db.flush()  # assign id for alert ref
    _maybe_alert(db, db.query(Vulnerability).filter(
        (Vulnerability.cve_id == (data.get("cve_id") or "")) |
        (Vulnerability.cnvd_id == (data.get("cnvd_id") or "")) |
        (Vulnerability.cnnvd_id == (data.get("cnnvd_id") or ""))
    ).first(), True)
    return "add"


def upsert_intel(db: Session, source: str, title: str, url: str, summary: str,
                 severity: str, ref_id: str, published_at: str) -> bool:
    dup = db.query(IntelItem).filter(
        IntelItem.source == source, IntelItem.title == title).first()
    if dup:
        return False
    db.add(IntelItem(source=source, title=title, url=url, summary=summary,
                     severity=severity, ref_id=ref_id, published_at=published_at))
    return True
