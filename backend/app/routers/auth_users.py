"""Login / logout / user management."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import current_user, hash_password, issue_token, require_role, revoke_token, verify_password
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class UserBody(BaseModel):
    username: str
    password: str = ""
    display_name: str = ""
    role: str = "viewer"
    enabled: bool = True


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    if not user.enabled:
        raise HTTPException(403, "账号已停用")
    return {
        "token": issue_token(user),
        "user": {"username": user.username, "display_name": user.display_name, "role": user.role},
    }


@router.post("/logout")
def logout(user: dict = Depends(current_user)):
    revoke_token(user["token"])
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"username": user["username"], "display_name": user["display_name"], "role": user["role"]}


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: dict = Depends(require_role("admin"))):
    return [
        {"id": u.id, "username": u.username, "display_name": u.display_name,
         "role": u.role, "enabled": u.enabled}
        for u in db.query(User).order_by(User.id).all()
    ]


@router.post("/users")
def create_user(body: UserBody, db: Session = Depends(get_db), user: dict = Depends(require_role("admin"))):
    if not body.password:
        raise HTTPException(400, "必须设置初始密码")
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(400, "角色必须是 admin/analyst/viewer")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    u = User(username=body.username, password_hash=hash_password(body.password),
             display_name=body.display_name or body.username, role=body.role, enabled=body.enabled)
    db.add(u)
    db.commit()
    return {"ok": True, "id": u.id}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserBody, db: Session = Depends(get_db), user: dict = Depends(require_role("admin"))):
    u = db.query(User).get(uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    if body.role not in ("admin", "analyst", "viewer"):
        raise HTTPException(400, "角色必须是 admin/analyst/viewer")
    if body.username != u.username and db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    u.username = body.username
    u.display_name = body.display_name or body.username
    u.role = body.role
    u.enabled = body.enabled
    if body.password:  # 只在填写时改密
        u.password_hash = hash_password(body.password)
    db.commit()
    return {"ok": True}


@router.delete("/users/{uid}")
def delete_user(uid: int, db: Session = Depends(get_db), user: dict = Depends(require_role("admin"))):
    admins = db.query(User).filter(User.role == "admin", User.enabled.is_(True)).count()
    target = db.query(User).get(uid)
    if not target:
        raise HTTPException(404, "用户不存在")
    if target.role == "admin" and admins <= 1:
        raise HTTPException(400, "至少保留一个管理员账号")
    if target.username == user["username"]:
        raise HTTPException(400, "不能删除自己")
    db.delete(target)
    db.commit()
    return {"ok": True}
