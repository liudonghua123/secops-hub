"""Knowledge base engine: chunking + lightweight keyword retrieval.

Offline-friendly (no embedding service required): chunks are scored by
term-overlap; good enough for playbook/regulation lookup. Swap in vector
retrieval later via agentscope.rag when an embedding service is available.
"""
import json
import re

from .database import SessionLocal
from .models import KnowledgeBase, KnowledgeDoc

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def split_chunks(text: str) -> list[str]:
    text = re.sub(r"\r\n", "\n", text or "")
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    for p in paras:
        start = 0
        while start < len(p):
            chunks.append(p[start:start + CHUNK_SIZE])
            start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks if chunks else ([text[:CHUNK_SIZE]] if text else [])


def _score(chunk: str, terms: list[str]) -> float:
    low = chunk.lower()
    return sum(low.count(t.lower()) for t in terms if t)


def search_kb(query: str, kb_name: str = "", top_k: int = 5) -> list[dict]:
    db = SessionLocal()
    try:
        terms = [t for t in re.split(r"[\s,，。;；?？]+", query or "") if t]
        if not terms:
            return []
        q = db.query(KnowledgeDoc)
        if kb_name:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.name.like(f"%{kb_name}%")).first()
            if not kb:
                return []
            q = q.filter(KnowledgeDoc.kb_id == kb.id)
        hits = []
        for doc in q.all():
            try:
                chunks = json.loads(doc.chunks or "[]")
            except json.JSONDecodeError:
                chunks = []
            for ch in chunks:
                s = _score(ch, terms)
                if s > 0:
                    hits.append({"score": s, "kb_doc": doc.filename, "text": ch[:400]})
        hits.sort(key=lambda h: -h["score"])
        return hits[:top_k]
    finally:
        db.close()
