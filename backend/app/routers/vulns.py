"""Vulnerabilities router: pagination, asset matching, disposal workflow."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import current_user, require_role
from ..database import get_db
from ..models import Alert, Asset, VulnEvent, Vulnerability

router = APIRouter(prefix="/api/vulns", tags=["vulns"])

STATUS_FLOW = {"未处置", "处置中", "已修复", "已忽略"}


class StatusBody(BaseModel):
    status: str
    note: str = ""


@router.get("")
def list_vulns(q: str = "", severity: str = "", source: str = "", status: str = "",
               page: int = 1, page_size: int = 20, with_total: bool = True,
               db: Session = Depends(get_db), user: dict = Depends(current_user)):
    query = db.query(Vulnerability)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Vulnerability.title.like(like), Vulnerability.cve_id.like(like),
                                 Vulnerability.cnnvd_id.like(like), Vulnerability.cnvd_id.like(like)))
    if severity:
        query = query.filter(Vulnerability.severity == severity)
    if source:
        query = query.filter(Vulnerability.source == source)
    if status:
        query = query.filter(Vulnerability.status == status)
    total = query.count() if with_total else 0
    items = (query.order_by(Vulnerability.cvss.desc(), Vulnerability.id.desc())
             .offset((page - 1) * page_size).limit(page_size).all())
    return {"total": total, "items": [enrich(v, db) for v in items]}


def enrich(v: Vulnerability, db: Session):
    """Attach matched assets (intelligence x asset fingerprint linkage)."""
    kws = [k.strip().lower() for k in v.affected_keywords.split(",") if k.strip()]
    assets = []
    if kws:
        for a in db.query(Asset).all():
            hay = f"{a.name} {a.fingerprint} {a.value}".lower()
            if any(k in hay for k in kws):
                assets.append({"id": a.id, "name": a.name, "value": a.value,
                               "criticality": a.criticality, "owner_dept": a.owner_dept})
    return v.__dict__ | {"created_at": str(v.created_at), "matched_assets": assets}


@router.get("/{vuln_id}")
def vuln_detail(vuln_id: int, db: Session = Depends(get_db), user: dict = Depends(current_user)):
    v = db.get(Vulnerability, vuln_id)
    if not v:
        raise HTTPException(404, "漏洞不存在")
    events = (db.query(VulnEvent).filter(VulnEvent.vuln_id == vuln_id)
              .order_by(VulnEvent.id.desc()).all())
    return enrich(v, db) | {"events": [
        {"id": e.id, "action": e.action, "detail": e.detail,
         "operator": e.operator, "created_at": str(e.created_at)} for e in events]}


@router.put("/{vuln_id}/status")
def set_status(vuln_id: int, body: StatusBody, db: Session = Depends(get_db),
               user: dict = Depends(require_role("analyst"))):
    v = db.get(Vulnerability, vuln_id)
    if not v:
        raise HTTPException(404, "漏洞不存在")
    if body.status not in STATUS_FLOW:
        raise HTTPException(400, "状态必须是 未处置/处置中/已修复/已忽略")
    old = v.status
    v.status = body.status
    db.add(VulnEvent(vuln_id=vuln_id, action="状态变更",
                     detail=f"{old} → {body.status}" + (f"｜{body.note}" if body.note else ""),
                     operator=user["username"]))
    # 修复/忽略后自动将对应预警标记为已读（闭环）
    if body.status in ("已修复", "已忽略"):
        db.query(Alert).filter(Alert.ref_type == "vuln", Alert.ref_id == vuln_id).update({"read": True})
    db.commit()
    return {"ok": True, "status": v.status}
