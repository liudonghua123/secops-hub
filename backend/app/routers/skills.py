"""Skills router: builtin catalog + upload + hub install + file view/edit.

Custom/hub skills are persisted as python files on the server
(SKILLS_DIR) and can be viewed/edited via GET/PUT /{skill_id}/code.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SkillItem
from ..skills_builtin import sync_builtin_skills
from ..skills_hub import hub_index, install_from_hub, resolve_manifest
from ..skills_store import (delete_skill_file, read_skill_file,
                             save_skill_file)

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillIn(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    code: str


class CodeIn(BaseModel):
    code: str


def _out(s: SkillItem) -> dict:
    return {"id": s.id, "name": s.name, "version": s.version, "source": s.source,
            "description": s.description, "enabled": s.enabled,
            "has_code": bool(s.code), "file_path": s.file_path}


@router.get("")
def list_skills(db: Session = Depends(get_db)):
    return [_out(s) for s in db.query(SkillItem).order_by(SkillItem.id).all()]


@router.post("/upload")
def upload_skill(data: SkillIn, db: Session = Depends(get_db)):
    """Upload a third-party skill pack (code must define tool_* functions).

    Code is saved as a server-side file and mirrored into the DB.
    """
    if "tool_" not in data.code:
        raise HTTPException(400, "技能代码需定义至少一个 tool_ 开头的函数")
    row = db.query(SkillItem).filter(SkillItem.name == data.name).first()
    path = save_skill_file(data.name, data.code)
    if row:
        row.version, row.description, row.code = data.version, data.description, data.code
        row.file_path = path
        row.source = "custom" if row.source == "custom" else row.source
        action = "updated"
    else:
        db.add(SkillItem(name=data.name, version=data.version, source="custom",
                          description=data.description, code=data.code,
                          file_path=path))
        action = "installed"
    db.commit()
    return {"ok": True, "action": action, "file_path": path}


@router.get("/{skill_id}/code")
def get_skill_code(skill_id: int, db: Session = Depends(get_db)):
    """View skill source code (from the server file when present)."""
    s = db.get(SkillItem, skill_id)
    if not s:
        raise HTTPException(404, "not found")
    if s.source == "builtin":
        raise HTTPException(400, "内置技能代码随平台内置，不提供在线编辑")
    code = read_skill_file(s.name)
    if code is None:
        code = s.code or ""
    return {"id": s.id, "name": s.name, "code": code, "file_path": s.file_path}


@router.put("/{skill_id}/code")
def update_skill_code(skill_id: int, data: CodeIn, db: Session = Depends(get_db)):
    """Edit skill source code: validate + persist to server file + DB mirror."""
    s = db.get(SkillItem, skill_id)
    if not s:
        raise HTTPException(404, "not found")
    if s.source == "builtin":
        raise HTTPException(400, "内置技能不可编辑")
    if "tool_" not in data.code:
        raise HTTPException(400, "技能代码需定义至少一个 tool_ 开头的函数")
    # syntax check before saving
    import ast
    try:
        ast.parse(data.code)
    except SyntaxError as exc:
        raise HTTPException(400, f"Python 语法错误：{exc.msg}（第 {exc.lineno} 行）")
    path = save_skill_file(s.name, data.code)
    s.code = data.code
    s.file_path = path
    db.commit()
    return {"ok": True, "file_path": path}


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
    delete_skill_file(s.name)
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
    r = install_from_hub(db, name, resolved["manifest"])
    if r.get("ok"):
        row = db.query(SkillItem).filter(SkillItem.name == name).first()
        if row:
            row.file_path = save_skill_file(name, row.code or "")
            db.commit()
            r["file_path"] = row.file_path
    return r


@router.post("/builtin/refresh")
def refresh_builtin(db: Session = Depends(get_db)):
    sync_builtin_skills()
    return {"ok": True}
