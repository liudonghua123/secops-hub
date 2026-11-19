"""Agent session router: per-agent conversations + chat turn execution."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agent_runtime import run_chat_turn
from ..ai_service import answer_rule_based
from ..database import get_db
from ..models import AgentMessage, AgentProfile, AgentSession

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionIn(BaseModel):
    agent_id: int
    title: str = ""


class ChatIn(BaseModel):
    content: str


@router.get("")
def list_sessions(agent_id: int, db: Session = Depends(get_db)):
    items = (db.query(AgentSession).filter(AgentSession.agent_id == agent_id)
             .order_by(AgentSession.updated_at.desc()).all())
    return [{"id": s.id, "agent_id": s.agent_id, "title": s.title,
             "updated_at": str(s.updated_at)} for s in items]


@router.post("")
def create_session(data: SessionIn, db: Session = Depends(get_db)):
    if not db.get(AgentProfile, data.agent_id):
        raise HTTPException(404, "agent not found")
    s = AgentSession(agent_id=data.agent_id, title=data.title or "新会话")
    db.add(s)
    db.commit()
    return {"id": s.id, "ok": True}


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    s = db.get(AgentSession, session_id)
    if not s:
        raise HTTPException(404, "not found")
    db.query(AgentMessage).filter(AgentMessage.session_id == session_id).delete()
    db.delete(s)
    db.commit()
    return {"ok": True}


@router.get("/{session_id}/messages")
def list_messages(session_id: int, db: Session = Depends(get_db)):
    items = (db.query(AgentMessage).filter(AgentMessage.session_id == session_id)
             .order_by(AgentMessage.id).all())
    return [{"id": m.id, "role": m.role, "content": m.content,
             "meta": json.loads(m.meta) if m.meta else {}, "created_at": str(m.created_at)}
            for m in items]


@router.post("/{session_id}/chat")
async def chat(session_id: int, data: ChatIn, db: Session = Depends(get_db)):
    """One chat turn: persisted history -> AgentScope ReActAgent -> persist reply.

    Degrades to the rule engine when LLM env is not configured.
    """
    s = db.get(AgentSession, session_id)
    if not s:
        raise HTTPException(404, "session not found")
    profile = db.get(AgentProfile, s.agent_id)
    if not profile or not profile.enabled:
        raise HTTPException(400, "agent 不可用")

    user_row = AgentMessage(session_id=session_id, role="user", content=data.content)
    db.add(user_row)
    db.commit()

    history = [{"role": m.role, "content": m.content}
               for m in db.query(AgentMessage).filter(AgentMessage.session_id == session_id)
               .order_by(AgentMessage.id).all() if m.id != user_row.id]

    try:
        result = await run_chat_turn(profile, history, data.content)
        role_meta = {"mode": "agentscope", "tools": result["meta"]["tools"],
                     "mcp_errors": result["meta"]["mcp_errors"], "model": result["meta"]["model"]}
        answer = result["answer"]
    except RuntimeError as exc:
        if str(exc) != "LLM_UNCONFIGURED":
            raise
        answer = answer_rule_based(data.content)
        role_meta = {"mode": "rule-engine",
                     "note": "未配置 LLM（LLM_API_BASE/LLM_API_KEY），当前为规则引擎降级应答"}
    except Exception as exc:
        import traceback

        answer = f"Agent 执行异常：{exc}\n{traceback.format_exc()[-600:]}"[:1200]
        role_meta = {"mode": "error"}

    reply_row = AgentMessage(session_id=session_id, role="assistant",
                             content=answer, meta=json.dumps(role_meta, ensure_ascii=False))
    db.add(reply_row)
    if s.title == "新会话":
        s.title = data.content[:20]
    db.commit()
    return {"answer": answer, "meta": role_meta, "message_id": reply_row.id}
