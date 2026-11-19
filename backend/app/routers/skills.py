"""Skills router: builtin catalog + upload + hub index/install."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SkillItem
from ..skills_builtin import sync_builtin_skills
from ..skills_hub import hub_index, install_from_hub, resolve_manifest

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillIn(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    code: str


@router.get("")
def list_skills(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "version": s.version, "source": s.source,
             "description": s.description, "enabled": s.enabled, "has_code": bool(s.code)}
            for s in db.query(SkillItem).order_by(SkillItem.id).all()]


@router.post("/upload")
def upload_skill(data: SkillIn, db: Session = Depends(get_db)):
    """Upload a third-party skill pack (code must define tool_* functions)."""
    if "tool_" not in data.code:
        raise HTTPException(400, "技能代码需定义至少一个 tool_ 开头的函数")
    row = db.query(SkillItem).filter(SkillItem.name == data.name).first()
    if row:
        row.version, row.description, row.code = data.version, data.description, data.code
        row.source = "custom" if row.source == "custom" else row.source
        action = "updated"
    else:
        db.add(SkillItem(name=data.name, version=data.version, source="custom",
                         description=data.description, code=data.code))
        action = "installed"
    db.commit()
    return {"ok": True, "action": action}


@router.put("/{skill_id}/toggle")
def toggle_skill(skill_id: int, db: Session = Depends(get_db)):
    s = db.get(SkillItem, skill_id)
    if not s:
        raise HTTPException(404, "not found")
    if s.source == "builtin":
        raise HTTPException(400, "内置技能不可停用")
    s.enabled = not s.enabled
    db.commit()
    return {"ok": True, "enabled": s.enabled}


@router.delete("/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    s = db.get(SkillItem, skill_id)
    if not s:
        raise HTTPException(404, "not found")
    if s.source == "builtin":
        raise HTTPException(400, "内置技能不可删除")
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.get("/hub")
def get_hub_index():
    return hub_index()


@router.post("/hub/install")
def hub_install(data: dict, db: Session = Depends(get_db)):
    """Install/update a skill from the hub. Body: {"name": "...", "url": "..."}."""
    name, url = data.get("name", ""), data.get("url", "")
    if not name:
        raise HTTPException(400, "缺少 name")
    resolved = resolve_manifest(name, url)
    if not resolved["ok"]:
        return resolved
    return install_from_hub(db, name, resolved["manifest"])


@router.post("/builtin/refresh")
def refresh_builtin(db: Session = Depends(get_db)):
    sync_builtin_skills()
    return {"ok": True}
