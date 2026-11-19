"""Data source synchronization router: NVD / CIRCL real fetch + CNVD/CNNVD import."""
import datetime

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from ..database import get_db
from ..fetchers.circl import sync_circl
from ..fetchers.importers import import_cnvd
from ..fetchers.nvd import sync_nvd
from ..models import SyncState

router = APIRouter(prefix="/api/sync", tags=["sync"])

SOURCE_INFO = [
    {"key": "nvd", "name": "NVD (NIST)", "mode": "api", "note": "实时 API 2.0，无 Key 限速 5 次/30 秒，可配置 NVD_API_KEY 提速"},
    {"key": "circl", "name": "CIRCL CVE", "mode": "api", "note": "备用实时源，返回最近 30 条新收录 CVE"},
    {"key": "cnvd", "name": "CNVD", "mode": "import", "note": "无公开 API，需单位账号在 cnvd.org.cn 导出增量文件后 JSON 导入"},
    {"key": "cnnvd", "name": "CNNVD", "mode": "import", "note": "API 需官方授权账号，导出文件后 JSON 导入（CNVD 通道同样适用）"},
]


def _mark(db: Session, key: str, detail: dict):
    state = db.get(SyncState, key)
    payload = {"at": datetime.datetime.now().isoformat(timespec="seconds"), "detail": detail}
    import json as _json
    if state:
        state.value = _json.dumps(payload, ensure_ascii=False)
    else:
        db.add(SyncState(key=key, value=_json.dumps(payload, ensure_ascii=False)))
    db.commit()


@router.get("/status")
def sync_status(db: Session = Depends(get_db)):
    import json as _json
    states = {s.key: s.value for s in db.query(SyncState).all()}
    out = []
    for s in SOURCE_INFO:
        last = _json.loads(states[s["key"]]) if s["key"] in states else None
        out.append(s | {"last_sync": last})
    return out


@router.post("/nvd")
def run_nvd(days: int = 7, max_results: int = 200, db: Session = Depends(get_db)):
    result = sync_nvd(db, days=days, max_results=max_results)
    if result.get("ok"):
        _mark(db, "nvd", result)
    return result


@router.post("/circl")
def run_circl(db: Session = Depends(get_db)):
    result = sync_circl(db)
    if result.get("ok"):
        _mark(db, "circl", result)
    return result


@router.post("/import")
def run_import(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Import CNVD/CNNVD batch export. Body: {"records": [...]} or a bare list,
    or {"raw": "<json text>"}. Optionally {"source": "CNVD"|"CNNVD"}."""
    raw = payload.get("raw") or payload.get("records") or payload
    source = str(payload.get("source", "CNVD"))
    result = import_cnvd(db, raw)
    if result.get("ok"):
        _mark(db, source.lower(), result)
        result["source"] = f"{source} import"
    return result
