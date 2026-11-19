"""Authentication: token sessions, role guards. Zero external deps."""
import hashlib
import hmac
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

# in-memory token store: token -> {username, role, expires}
_SESSIONS: dict[str, dict] = {}
TOKEN_TTL = 12 * 3600  # 12h

ROLES = {"admin": 3, "analyst": 2, "viewer": 1}


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def issue_token(user: User) -> str:
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "username": user.username,
        "role": user.role,
        "exp": time.time() + TOKEN_TTL,
    }
    return token


def revoke_token(token: str):
    _SESSIONS.pop(token, None)


def current_user(request: Request, db: Session = Depends(get_db)) -> dict:
    """Resolve Authorization: Bearer <token> to a user context dict."""
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "未登录或令牌缺失")
    info = _SESSIONS.get(token)
    if not info or info["exp"] < time.time():
        _SESSIONS.pop(token, None)
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.query(User).filter(User.username == info["username"]).first()
    if not user or not user.enabled:
        raise HTTPException(401, "账号不可用")
    return {"username": user.username, "role": user.role, "display_name": user.display_name or user.username, "token": token}


def require_role(minimum: str):
    """Dependency factory: viewer < analyst < admin."""
    threshold = ROLES[minimum]

    def guard(user: dict = Depends(current_user)):
        if ROLES.get(user["role"], 0) < threshold:
            raise HTTPException(403, "权限不足：该操作需要 " + minimum + " 角色")
        return user

    return guard
