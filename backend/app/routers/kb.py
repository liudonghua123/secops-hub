"""Knowledge base router: CRUD + document upload (chunked for retrieval)."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..kb_engine import split_chunks
from ..models import KnowledgeBase, KnowledgeDoc

router = APIRouter(prefix="/api/kb", tags=["kb"])

MAX_DOC = 2 * 1024 * 1024  # 2 MB text per doc


class KBIn(BaseModel):
    name: str
    description: str = ""


class DocIn(BaseModel):
    filename: str
    content: str


@router.get("")
def list_kbs(db: Session = Depends(get_db)):
    out = []
    for k in db.query(KnowledgeBase).order_by(KnowledgeBase.id).all():
        docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == k.id).all()
        out.append({"id": k.id, "name": k.name, "description": k.description,
                    "doc_count": len(docs),
                    "chunk_total": sum(len(d.chunks) // 100 for d in docs)})  # approx
    return out


@router.post("")
def create_kb(data: KBIn, db: Session = Depends(get_db)):
    k = KnowledgeBase(name=data.name, description=data.description)
    db.add(k)
    db.commit()
    return {"id": k.id, "ok": True}


@router.put("/{kb_id}")
def update_kb(kb_id: int, data: KBIn, db: Session = Depends(get_db)):
    k = db.get(KnowledgeBase, kb_id)
    if not k:
        raise HTTPException(404, "not found")
    k.name, k.description = data.name, data.description
    db.commit()
    return {"ok": True}


@router.delete("/{kb_id}")
def delete_kb(kb_id: int, db: Session = Depends(get_db)):
    k = db.get(KnowledgeBase, kb_id)
    if not k:
        raise HTTPException(404, "not found")
    db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kb_id).delete()
    db.delete(k)
    db.commit()
    return {"ok": True}


@router.get("/{kb_id}/docs")
def list_docs(kb_id: int, db: Session = Depends(get_db)):
    return [{"id": d.id, "filename": d.filename, "size": d.size,
             "chunks": len((d.chunks or "[]")) and len(__import__("json").loads(d.chunks or "[]")),
             "created_at": str(d.created_at)}
            for d in db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kb_id).all()]


def _add_doc(db: Session, kb_id: int, filename: str, content: str) -> dict:
    if len(content) > MAX_DOC:
        raise HTTPException(400, "文档过大（>2MB），请拆分后上传")
    chunks = split_chunks(content)
    import json as _json
    d = KnowledgeDoc(kb_id=kb_id, filename=filename, content=content,
                     chunks=_json.dumps(chunks, ensure_ascii=False), size=len(content))
    db.add(d)
    db.commit()
    return {"id": d.id, "chunks": len(chunks), "ok": True}


@router.post("/{kb_id}/docs")
def add_doc(kb_id: int, data: DocIn, db: Session = Depends(get_db)):
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(404, "kb not found")
    return _add_doc(db, kb_id, data.filename, data.content)


@router.post("/{kb_id}/docs/upload")
async def upload_doc(kb_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Multipart file upload (.txt / .md / .csv / source code as plain text)."""
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(404, "kb not found")
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        content = raw.decode("gbk", errors="replace")
    return _add_doc(db, kb_id, file.filename or "doc.txt", content)


@router.delete("/{kb_id}/docs/{doc_id}")
def delete_doc(kb_id: int, doc_id: int, db: Session = Depends(get_db)):
    d = db.get(KnowledgeDoc, doc_id)
    if not d or d.kb_id != kb_id:
        raise HTTPException(404, "not found")
    db.delete(d)
    db.commit()
    return {"ok": True}


@router.get("/{kb_id}/search")
def kb_search_api(kb_id: int, q: str, db: Session = Depends(get_db)):
    k = db.get(KnowledgeBase, kb_id)
    if not k:
        raise HTTPException(404, "kb not found")
    from ..kb_engine import search_kb
    return search_kb(q, kb_name=k.name)
