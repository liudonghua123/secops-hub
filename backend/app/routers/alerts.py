"""In-app alert center: auto alerts for critical/high vulns with matching assets."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def push_alert(db: Session, level: str, title: str, detail: str = "",
               ref_type: str = "vuln", ref_id: int = 0):
    """Create alert unless an unread one for the same ref already exists."""
    exists = (db.query(Alert)
              .filter(Alert.ref_type == ref_type, Alert.ref_id == ref_id, Alert.read.is_(False))
              .first())
    if exists:
        return None
    a = Alert(level=level, title=title, detail=detail, ref_type=ref_type, ref_id=ref_id)
    db.add(a)
    return a


@router.get("")
def list_alerts(only_unread: bool = False, limit: int = 50,
                db: Session = Depends(get_db), user: dict = Depends(current_user)):
    query = db.query(Alert).order_by(Alert.id.desc())
    if only_unread:
        query = query.filter(Alert.read.is_(False))
    items = query.limit(limit).all()
    unread = db.query(Alert).filter(Alert.read.is_(False)).count()
    return {"unread": unread, "items": [
        {"id": a.id, "level": a.level, "title": a.title, "detail": a.detail,
         "ref_type": a.ref_type, "ref_id": a.ref_id, "read": a.read,
         "created_at": str(a.created_at)} for a in items]}


class ReadBody(BaseModel):
    ids: list[int] = []
    all: bool = False


@router.post("/read")
def mark_read(body: ReadBody, db: Session = Depends(get_db), user: dict = Depends(current_user)):
    query = db.query(Alert)
    if body.all:
        query = query.filter(Alert.read.is_(False))
    else:
        query = query.filter(Alert.id.in_(body.ids))
    n = query.update({"read": True}, synchronize_session=False)
    db.commit()
    return {"ok": True, "marked": n}
