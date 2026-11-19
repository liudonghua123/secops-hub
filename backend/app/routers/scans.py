"""Scan tasks router: task orchestration + finding review loop.

Engine adapter layer: 'nuclei' / 'poc-suite' / 'weak-pass' engines are stubbed
with a simulated executor. Real engine integration point is `run_engine()`.
"""
import random

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Finding, ScanTask
from ..nuclei import nuclei_status, run_nuclei

router = APIRouter(prefix="/api/scans", tags=["scans"])

ENGINES = {
    "nuclei": "Nuclei POC 引擎",
    "poc-suite": "多引擎 POC 套件 (Nuclei+Xray+GoPOC)",
    "weak-pass": "弱口令检测引擎",
}


def run_engine(engine: str, scope: str) -> list[dict]:
    """Run the requested engine. Nuclei uses the real binary when installed;
    everything else (and nuclei fallback) uses the simulated executor.
    Replace simulation with subprocess adapters for Xray/GoPOC as needed.
    """
    if engine in ("nuclei", "poc-suite") and nuclei_status()["available"]:
        return run_nuclei(scope)
    if random.random() < 0.15 or not scope:
        return []
    return [
        {"asset_value": scope.split(",")[0].strip(), "vuln_title": "后台管理口令强度不足", "severity": "中危",
         "poc_ref": "weak-pass", "evidence": "模拟结果：默认口令命中"},
    ]


@router.get("/nuclei-status")
def get_nuclei_status():
    return nuclei_status()


class TaskIn(BaseModel):
    name: str
    target_scope: str
    engine: str = "nuclei"


@router.get("")
def list_tasks(db: Session = Depends(get_db)):
    return [t.__dict__ | {"created_at": str(t.created_at)} for t in db.query(ScanTask).all()]


@router.get("/engines")
def engines():
    return [{"key": k, "name": v} for k, v in ENGINES.items()]


@router.post("")
def create_task(data: TaskIn, db: Session = Depends(get_db)):
    t = ScanTask(name=data.name, target_scope=data.target_scope, engine=data.engine,
                 status="待执行")
    db.add(t)
    db.commit()
    return {"id": t.id, "ok": True}


@router.post("/{task_id}/start")
def start_task(task_id: int, db: Session = Depends(get_db)):
    """Start scan: simulated engine run, generate findings for review."""
    t = db.get(ScanTask, task_id)
    if not t:
        return {"error": "not found"}
    t.status = "执行中"
    t.started_at = "2026-11-19 (模拟)"
    findings = run_engine(t.engine, t.target_scope)
    for f in findings:
        db.add(Finding(task_id=task_id, **f))
    t.progress = min(100, t.progress + 20)
    if t.progress >= 100:
        t.status = "已完成"
        t.finished_at = "2026-11-19 (模拟)"
    db.commit()
    return {"ok": True, "status": t.status, "new_findings": len(findings)}


@router.get("/{task_id}/findings")
def task_findings(task_id: int, db: Session = Depends(get_db)):
    items = db.query(Finding).filter(Finding.task_id == task_id).all()
    return [f.__dict__ | {"created_at": str(f.created_at)} for f in items]


@router.put("/findings/{finding_id}/review")
def review_finding(finding_id: int, data: dict, db: Session = Depends(get_db)):
    """Human review gate: confirm as real vuln or mark false positive."""
    f = db.get(Finding, finding_id)
    if not f:
        return {"error": "not found"}
    action = data.get("action")  # confirm / false_positive
    if action == "confirm":
        f.verified, f.false_positive = True, False
    elif action == "false_positive":
        f.verified, f.false_positive = False, True
    f.reviewed_by = data.get("reviewer", "analyst")
    db.commit()
    return {"ok": True}
