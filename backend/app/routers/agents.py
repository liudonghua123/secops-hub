"""Agent profile management router."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..agent_runtime import llm_configured
from ..database import get_db
from ..models import AgentProfile, AgentSession, KnowledgeBase, MCPServer, SkillItem

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentIn(BaseModel):
    name: str
    description: str = ""
    sys_prompt: str = "你是单位网络安全值守助手。"
    model_name: str = ""
    mcp_ids: list[int] = []
    skill_ids: list[int] = []
    kb_ids: list[int] = []
    max_iters: int = 10
    enabled: bool = True


def _serialize(a: AgentProfile, db: Session) -> dict:
    mcp_ids = json.loads(a.mcp_ids or "[]")
    skill_ids = json.loads(a.skill_ids or "[]")
    kb_ids = json.loads(a.kb_ids or "[]")
    mcps = db.query(MCPServer).filter(MCPServer.id.in_(mcp_ids)).all() if mcp_ids else []
    skills = db.query(SkillItem).filter(SkillItem.id.in_(skill_ids)).all() if skill_ids else []
    kbs = db.query(KnowledgeBase).filter(KnowledgeBase.id.in_(kb_ids)).all() if kb_ids else []
    return {
        "id": a.id, "name": a.name, "description": a.description,
        "sys_prompt": a.sys_prompt, "model_name": a.model_name,
        "max_iters": a.max_iters, "enabled": a.enabled,
        "mcp_ids": mcp_ids, "skill_ids": skill_ids, "kb_ids": kb_ids,
        "mcp": [{"id": m.id, "name": m.name, "transport": m.transport, "status": m.status} for m in mcps],
        "skills": [{"id": s.id, "name": s.name, "source": s.source, "version": s.version} for s in skills],
        "kbs": [{"id": k.id, "name": k.name} for k in kbs],
        "session_count": db.query(AgentSession).filter(AgentSession.agent_id == a.id).count(),
        "created_at": str(a.created_at),
    }


@router.get("")
def list_agents(db: Session = Depends(get_db)):
    return [_serialize(a, db) for a in db.query(AgentProfile).order_by(AgentProfile.id).all()]


@router.get("/options")
def binding_options(db: Session = Depends(get_db)):
    """All bindable mcp/skills/kb for the editor UI."""
    return {
        "mcp": [{"id": m.id, "name": m.name, "transport": m.transport,
                 "status": m.status, "enabled": m.enabled}
                for m in db.query(MCPServer).order_by(MCPServer.id).all()],
        "skills": [{"id": s.id, "name": s.name, "source": s.source,
                    "version": s.version, "enabled": s.enabled}
                   for s in db.query(SkillItem).order_by(SkillItem.id).all()],
        "kbs": [{"id": k.id, "name": k.name} for k in db.query(KnowledgeBase).order_by(KnowledgeBase.id).all()],
        "llm": {"configured": llm_configured(),
                "default_model": __import__("os").environ.get("LLM_MODEL", "")},
    }


@router.post("")
def create_agent(data: AgentIn, db: Session = Depends(get_db)):
    a = AgentProfile(
        name=data.name, description=data.description, sys_prompt=data.sys_prompt,
        model_name=data.model_name, max_iters=data.max_iters, enabled=data.enabled,
        mcp_ids=json.dumps(data.mcp_ids), skill_ids=json.dumps(data.skill_ids),
        kb_ids=json.dumps(data.kb_ids),
    )
    db.add(a)
    db.commit()
    return {"id": a.id, "ok": True}


@router.put("/{agent_id}")
def update_agent(agent_id: int, data: AgentIn, db: Session = Depends(get_db)):
    a = db.get(AgentProfile, agent_id)
    if not a:
        raise HTTPException(404, "agent not found")
    a.name, a.description = data.name, data.description
    a.sys_prompt, a.model_name = data.sys_prompt, data.model_name
    a.max_iters, a.enabled = data.max_iters, data.enabled
    a.mcp_ids = json.dumps(data.mcp_ids)
    a.skill_ids = json.dumps(data.skill_ids)
    a.kb_ids = json.dumps(data.kb_ids)
    db.commit()
    return {"ok": True}


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    a = db.get(AgentProfile, agent_id)
    if not a:
        raise HTTPException(404, "agent not found")
    db.delete(a)
    db.commit()
    return {"ok": True}
