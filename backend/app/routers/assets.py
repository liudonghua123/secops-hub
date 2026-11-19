"""Assets router: pagination, batch import/export (xlsx/csv), profile."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import current_user, require_role
from ..database import get_db
from ..models import Asset

router = APIRouter(prefix="/api/assets", tags=["assets"])

IMPORT_COLUMNS = ["名称", "类型", "值", "责任部门", "重要性", "备案号", "互联网暴露", "指纹"]


class AssetIn(BaseModel):
    name: str
    type: str = "domain"
    value: str
    owner_dept: str = ""
    criticality: str = "中"
    icp_no: str = ""
    exposure: bool = False
    fingerprint: str = ""


@router.get("")
def list_assets(q: str = "", type: str = "", criticality: str = "",
                page: int = 1, page_size: int = 20, with_total: bool = True,
                db: Session = Depends(get_db), user: dict = Depends(current_user)):
    query = db.query(Asset)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Asset.name.like(like), Asset.value.like(like),
                                 Asset.owner_dept.like(like)))
    if type:
        query = query.filter(Asset.type == type)
    if criticality:
        query = query.filter(Asset.criticality == criticality)
    total = query.count() if with_total else 0
    items = (query.order_by(Asset.id)
             .offset((page - 1) * page_size).limit(page_size).all())
    return {"total": total, "items": [a.__dict__ | {"created_at": str(a.created_at)} for a in items]}


@router.post("")
def create_asset(data: AssetIn, db: Session = Depends(get_db),
                 user: dict = Depends(require_role("analyst"))):
    a = Asset(**data.model_dump())
    db.add(a)
    db.commit()
    return {"id": a.id, "ok": True}


@router.put("/{asset_id}")
def update_asset(asset_id: int, data: AssetIn, db: Session = Depends(get_db),
                 user: dict = Depends(require_role("analyst"))):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "asset not found")
    for k, v in data.model_dump().items():
        setattr(a, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db),
                 user: dict = Depends(require_role("admin"))):
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "asset not found")
    db.delete(a)
    db.commit()
    return {"ok": True}


# ---------- batch import / export ----------

def _parse_bool(v) -> bool:
    return str(v).strip().lower() in ("是", "true", "1", "yes", "y")


def _row_to_asset(row: list) -> dict | None:
    """row: [名称, 类型, 值, 责任部门, 重要性, 备案号, 互联网暴露, 指纹]"""
    if not row or not str(row[0] or "").strip():
        return None
    pad = (row + [""] * 8)[:8]
    return {
        "name": str(pad[0]).strip(),
        "type": str(pad[1]).strip() or "domain",
        "value": str(pad[2]).strip(),
        "owner_dept": str(pad[3]).strip(),
        "criticality": str(pad[4]).strip() or "中",
        "icp_no": str(pad[5]).strip(),
        "exposure": _parse_bool(pad[6]),
        "fingerprint": str(pad[7]).strip(),
    }


@router.post("/import")
async def import_assets(file: UploadFile, db: Session = Depends(get_db),
                        user: dict = Depends(require_role("analyst"))):
    """xlsx or csv batch import. Matched by 名称+值: update if exists else insert."""
    filename = (file.filename or "").lower()
    raw = await file.read()
    rows = []
    if filename.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), read_only=True)
        ws = wb.active
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:  # header
                continue
            rows.append(list(row))
    else:  # csv
        text = raw.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        for i, row in enumerate(reader):
            if i == 0:
                continue
            rows.append(row)

    added = updated = skipped = 0
    errors = []
    for n, row in enumerate(rows, start=2):
        try:
            data = _row_to_asset(row)
            if not data:
                skipped += 1
                continue
            existing = (db.query(Asset)
                        .filter(Asset.name == data["name"], Asset.value == data["value"])
                        .first())
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(Asset(**data))
                added += 1
        except Exception as exc:
            errors.append(f"第{n}行: {exc}")
    db.commit()
    return {"ok": True, "added": added, "updated": updated, "skipped": skipped, "errors": errors[:10]}


@router.get("/export")
def export_assets(format: str = "xlsx", db: Session = Depends(get_db),
                  user: dict = Depends(current_user)):
    items = db.query(Asset).order_by(Asset.id).all()
    rows = [[a.name, a.type, a.value, a.owner_dept, a.criticality,
             a.icp_no, "是" if a.exposure else "否", a.fingerprint] for a in items]
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(IMPORT_COLUMNS)
        writer.writerows(rows)
        return StreamingResponse(iter([buf.getvalue().encode("utf-8-sig")]), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=assets.csv"})
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "资产清单"
    ws.append(IMPORT_COLUMNS)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf,
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": "attachment; filename=assets.xlsx"})


@router.get("/{asset_id}/profile")
def asset_profile(asset_id: int, db: Session = Depends(get_db),
                  user: dict = Depends(current_user)):
    """Multi-dimension asset profile (borrowed from ARL-Next asset portrait)."""
    a = db.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, "asset not found")
    keywords = [k.strip() for k in a.fingerprint.split(",") if k.strip()]
    from ..models import Vulnerability
    matched = []
    for v in db.query(Vulnerability).all():
        kws = [k.strip().lower() for k in v.affected_keywords.split(",") if k.strip()]
        if any(k in a.fingerprint.lower() or k in a.name.lower() for k in kws):
            matched.append({
                "id": v.id, "title": v.title, "severity": v.severity,
                "cve_id": v.cve_id, "cnvd_id": v.cnvd_id, "cnnvd_id": v.cnnvd_id,
                "poc_available": v.poc_available, "status": v.status,
            })
    return {
        "asset": a.__dict__ | {"created_at": str(a.created_at)},
        "fingerprint_list": keywords,
        "matched_vulns": matched,
        "risk_score": sum({"严重": 10, "高危": 7, "中危": 4, "低危": 1}.get(m["severity"], 0) for m in matched),
    }
