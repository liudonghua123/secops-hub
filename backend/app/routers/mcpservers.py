"""MCP server registry router: CRUD + live connection test."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MCPServer

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class MCPServerIn(BaseModel):
    name: str
    transport: str = "http"  # stdio/http
    command: str = ""
    args: list[str] = []
    url: str = ""
    headers: dict = {}
    enabled: bool = True
    note: str = ""


@router.get("")
def list_servers(db: Session = Depends(get_db)):
    return [m.__dict__ | {"created_at": str(m.created_at)}
            for m in db.query(MCPServer).order_by(MCPServer.id).all()]


@router.post("")
def create_server(data: MCPServerIn, db: Session = Depends(get_db)):
    m = MCPServer(name=data.name, transport=data.transport, command=data.command,
                  args=json.dumps(data.args), url=data.url,
                  headers=json.dumps(data.headers), enabled=data.enabled, note=data.note)
    db.add(m)
    db.commit()
    return {"id": m.id, "ok": True}


@router.put("/{server_id}")
def update_server(server_id: int, data: MCPServerIn, db: Session = Depends(get_db)):
    m = db.get(MCPServer, server_id)
    if not m:
        raise HTTPException(404, "not found")
    m.name, m.transport = data.name, data.transport
    m.command, m.args = data.command, json.dumps(data.args)
    m.url, m.headers = data.url, json.dumps(data.headers)
    m.enabled, m.note = data.enabled, data.note
    db.commit()
    return {"ok": True}


@router.delete("/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db)):
    m = db.get(MCPServer, server_id)
    if not m:
        raise HTTPException(404, "not found")
    db.delete(m)
    db.commit()
    return {"ok": True}


@router.post("/{server_id}/test")
async def test_server(server_id: int, db: Session = Depends(get_db)):
    """Live connect + list tools. stdio spawns the process; http opens streamable-http."""
    m = db.get(MCPServer, server_id)
    if not m:
        raise HTTPException(404, "not found")
    from agentscope.mcp import HttpStatelessClient, StdIOStatefulClient

    client = None
    try:
        if m.transport == "stdio":
            client = StdIOStatefulClient(name=m.name, command=m.command,
                                         args=json.loads(m.args or "[]"))
            await client.connect()
        else:
            client = HttpStatelessClient(name=m.name, transport="streamable_http",
                                         url=m.url, headers=json.loads(m.headers or "{}"))
        tools = await client.list_tools()
        names = [t.name for t in (tools or [])]
        m.status, m.tool_count = "正常", len(names)
        db.commit()
        return {"ok": True, "tools": names}
    except Exception as exc:
        m.status, m.tool_count = "失败", 0
        db.commit()
        return {"ok": False, "error": str(exc)[:300]}
    finally:
        if client is not None and hasattr(client, "close") and m.transport == "stdio":
            try:
                await client.close()
            except Exception:
                pass
