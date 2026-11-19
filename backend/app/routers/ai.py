"""AI router."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai_service import answer_rule_based, llm_available, llm_chat, vuln_brief
from ..auth import current_user
from ..database import get_db
from ..models import Vulnerability
from .vulns import enrich

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def ai_status(user: dict = Depends(current_user)):
    return {"llm_available": llm_available(), "mode": "llm" if llm_available() else "rule-engine"}


@router.get("/vuln-brief/{vuln_id}")
def vuln_brief_api(vuln_id: int, db: Session = Depends(get_db), user: dict = Depends(current_user)):
    v = db.get(Vulnerability, vuln_id)
    if not v:
        return {"error": "not found"}
    data = enrich(v, db)
    return {"vuln_id": vuln_id, "brief": vuln_brief(data), "mode": "llm" if llm_available() else "rule-engine"}


class AskIn(BaseModel):
    question: str


@router.post("/chat")
def chat(data: AskIn, db: Session = Depends(get_db), user: dict = Depends(current_user)):
    """AI chat assistant with lightweight data grounding."""
    q = data.question
    context = ""
    for v in db.query(Vulnerability).all():
        if any(k and k in q for k in {v.cve_id, v.cnvd_id, v.cnnvd_id, v.title}):
            context += f"\n匹配漏洞: {v.title} 级别:{v.severity} 影响:{v.affected_keywords}"
            context += f" 受影响资产: {[a['name'] for a in enrich(v, db)['matched_assets']]}"
    if llm_available():
        messages = [
            {"role": "system", "content": "你是单位网络安全值守助手，基于平台数据回答，简体中文，简洁专业。"},
            {"role": "user", "content": (f"平台内相关信息：{context}" if context else "") + "\n问题：" + q},
        ]
        answer = llm_chat(messages)
        mode = "llm"
    if not llm_available() or not answer:
        answer, mode = answer_rule_based(q) + (("\n\n检索到相关漏洞信息：" + context) if context else ""), "rule-engine"
    return {"answer": answer, "mode": mode}
