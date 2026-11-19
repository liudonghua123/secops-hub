"""Threat intelligence router: aggregated intel feed (borrowed from threat-broadcast)."""
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import IntelItem, Vulnerability

router = APIRouter(prefix="/api/intel", tags=["intel"])

SOURCES = ["CNNVD", "CNVD", "NVD", "360CERT", "奇安信", "绿盟", "OSCS", "安全客"]


@router.get("")
def list_intel(q: str = "", source: str = "", severity: str = "",
               db: Session = Depends(get_db)):
    query = db.query(IntelItem)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(IntelItem.title.like(like), IntelItem.summary.like(like),
                                 IntelItem.ref_id.like(like)))
    if source:
        query = query.filter(IntelItem.source == source)
    if severity:
        query = query.filter(IntelItem.severity == severity)
    items = query.order_by(IntelItem.published_at.desc()).all()
    return [i.__dict__ | {"created_at": str(i.created_at)} for i in items]


@router.get("/sources")
def source_stats(db: Session = Depends(get_db)):
    items = db.query(IntelItem).all()
    stats: dict = {}
    for i in items:
        stats[i.source] = stats.get(i.source, 0) + 1
    return [{"source": k, "count": v} for k, v in sorted(stats.items(), key=lambda x: -x[1])]


@router.get("/{intel_id}/related-vulns")
def related_vulns(intel_id: int, db: Session = Depends(get_db)):
    """Link intel item to local vulnerability library by ref id."""
    i = db.get(IntelItem, intel_id)
    if not i:
        return {"error": "not found"}
    ref = (i.ref_id or "").strip()
    vulns = []
    if ref:
        vulns = db.query(Vulnerability).filter(
            or_(Vulnerability.cve_id == ref, Vulnerability.cnvd_id == ref,
                Vulnerability.cnnvd_id == ref)).all()
    return {"intel": i.__dict__ | {"created_at": str(i.created_at)},
            "vulns": [v.__dict__ | {"created_at": str(v.created_at)} for v in vulns]}
