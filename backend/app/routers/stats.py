"""Dashboard statistics router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Asset, Finding, IntelItem, ScanTask, Vulnerability

router = APIRouter(prefix="/api/stats", tags=["stats"])

SEV_ORDER = ["严重", "高危", "中危", "低危"]


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    vulns = db.query(Vulnerability).all()
    findings = db.query(Finding).all()
    tasks = db.query(ScanTask).all()
    sev_dist = {s: sum(1 for v in vulns if v.severity == s) for s in SEV_ORDER}
    return {
        "asset_total": len(assets),
        "asset_exposed": sum(1 for a in assets if a.exposure),
        "vuln_total": len(vulns),
        "vuln_unresolved": sum(1 for v in vulns if v.status == "未处置"),
        "sev_distribution": sev_dist,
        "intel_total": db.query(IntelItem).count(),
        "task_total": len(tasks),
        "task_running": sum(1 for t in tasks if t.status == "执行中"),
        "finding_total": len(findings),
        "finding_verified": sum(1 for f in findings if f.verified),
        "finding_fp": sum(1 for f in findings if f.false_positive),
    }


@router.get("/trend")
def trend(db: Session = Depends(get_db)):
    """Vulnerability publish trend by month."""
    vulns = db.query(Vulnerability).all()
    buckets: dict = {}
    for v in vulns:
        month = (v.published_at or "")[:7]
        if month:
            buckets[month] = buckets.get(month, 0) + 1
    return [{"month": k, "count": v} for k, v in sorted(buckets.items())]


@router.get("/top-risks")
def top_risks(db: Session = Depends(get_db)):
    vulns = db.query(Vulnerability).order_by(Vulnerability.cvss.desc()).limit(6).all()
    return [{"title": v.title, "severity": v.severity, "cvss": v.cvss,
             "id": v.id, "poc_available": v.poc_available} for v in vulns]
