"""Knowledge base router: CRUD + folder-tree documents + batch upload.

The KB is a *library/directory* model: each knowledge base is a
library; documents live inside a folder tree (``folder`` path column,
"" = root). Supports multi-file upload and paste-in at any directory,
tree browsing, search within library.
"""
import json
import posixpath

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
    folder: str = ""


class FolderIn(BaseModel):
    path: str  # new folder path relative to library root, e.g. "预案/网络"


def _norm_folder(folder: str) -> str:
    """Normalize a folder path: 'a//b/' -> 'a/b'; '.'/'/' -> ''."""
    parts = [p for p in (folder or "").replace("\\", "/").split("/") if p]
    parts = [p for p in parts if p not in (".", "..")]
    return "/".join(parts)[:280]


def _doc_out(d: KnowledgeDoc) -> dict:
    try:
        n_chunks = len(json.loads(d.chunks or "[]"))
    except json.JSONDecodeError:
        n_chunks = 0
    return {"id": d.id, "folder": d.folder or "", "filename": d.filename,
            "size": d.size, "chunks": n_chunks, "created_at": str(d.created_at)}


@router.get("")
def list_kbs(db: Session = Depends(get_db)):
    out = []
    for k in db.query(KnowledgeBase).order_by(KnowledgeBase.id).all():
        docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == k.id).all()
        folders = sorted({d.folder or "" for d in docs})
        out.append({"id": k.id, "name": k.name, "description": k.description,
                    "doc_count": len(docs),
                    "folder_count": len([f for f in folders if f]),
                    "chunk_total": sum(len(json.loads(d.chunks or "[]")) for d in docs)})
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
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(404, "kb not found")
    docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kb_id).all()
    tree: dict = {}
    for d in docs:
        node = tree
        for seg in (d.folder or "").split("/"):
            if seg:
                node = node.setdefault(seg, {})
        node.setdefault("__files__", []).append(_doc_out(d))

    def to_list(node: dict) -> list:
        out = []
        for name in sorted(k for k in node if k != "__files__"):
            children = to_list(node[name])
            files = node[name].get("__files__", [])
            out.append({"type": "folder", "name": name,
                        "children": children, "file_count": len(files) + sum(
                            c["file_count"] for c in children if c["type"] == "folder")})
        for f in node.get("__files__", []):
            out.append({"type": "file", **f})
        return out

    return to_list(tree)


@router.post("/{kb_id}/folders")
def create_folder(kb_id: int, data: FolderIn, db: Session = Depends(get_db)):
    """Create a folder. Folders materialize implicitly with docs, but a
    placeholder marker lets empty folders exist in the tree."""
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(404, "kb not found")
    folder = _norm_folder(data.path)
    if not folder:
        raise HTTPException(400, "目录路径无效")
    exists = db.query(KnowledgeDoc).filter(
        KnowledgeDoc.kb_id == kb_id, KnowledgeDoc.folder == folder).first()
    if not exists:
        db.add(KnowledgeDoc(kb_id=kb_id, folder=folder, filename="",
                             content="", chunks="[]", size=0))
        db.commit()
    return {"ok": True, "folder": folder}


@router.delete("/{kb_id}/folders")
def delete_folder(kb_id: int, path: str, db: Session = Depends(get_db)):
    """Delete a folder and everything inside it."""
    folder = _norm_folder(path)
    q = db.query(KnowledgeDoc).filter(KnowledgeDoc.kb_id == kb_id)
    if folder:
        q = q.filter(KnowledgeDoc.folder == folder)  # exact path
        # also delete subfolders
        import sqlalchemy as _sa
        q2 = db.query(KnowledgeDoc).filter(
            KnowledgeDoc.kb_id == kb_id,
            _sa.or_(KnowledgeDoc.folder.like(f"{folder}/%"),
                    KnowledgeDoc.folder == folder))
        q2.delete(synchronize_session=False)
    else:
        q.delete(synchronize_session=False)
    db.commit()
    return {"ok": True}


def _add_doc(db: Session, kb_id: int, filename: str, content: str,
             folder: str = "") -> dict:
    if len(content) > MAX_DOC:
        raise HTTPException(400, "文档过大（>2MB），请拆分后上传")
    folder = _norm_folder(folder)
    chunks = split_chunks(content)
    d = KnowledgeDoc(kb_id=kb_id, folder=folder, filename=filename,
                     content=content,
                     chunks=json.dumps(chunks, ensure_ascii=False),
                     size=len(content))
    db.add(d)
    db.commit()
    return {"id": d.id, "chunks": len(chunks), "folder": folder, "ok": True}


@router.post("/{kb_id}/docs")
def add_doc(kb_id: int, data: DocIn, db: Session = Depends(get_db)):
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(404, "kb not found")
    return _add_doc(db, kb_id, data.filename, data.content, data.folder)


@router.post("/{kb_id}/docs/upload")
async def upload_doc(kb_id: int, file: list[UploadFile] = File(...),
                     folder: str = "", db: Session = Depends(get_db)):
    """Batch multipart upload (.txt/.md/.csv/source code as plain text).

    Accepts multiple files at once; all land in ``folder``.
    """
    if not db.get(KnowledgeBase, kb_id):
        raise HTTPException(404, "kb not found")
    folder = _norm_folder(folder)
    results = []
    for f in file:
        raw = await f.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("gbk", errors="replace")
        try:
            r = _add_doc(db, kb_id, f.filename or "doc.txt", content, folder)
        except HTTPException as exc:
            r = {"filename": f.filename, "ok": False, "error": exc.detail}
        results.append({"filename": f.filename, **r})
    return {"ok": True, "items": results}


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
