"""SecOps Hub backend entry.

FastAPI on port 8100; MCP (streamable HTTP) mounted at /mcp on the SAME port.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .seed import run_seed

try:
    from mcp.server.mcpserver import MCPServer  # noqa: F401
    from mcp.server.transport_security import TransportSecuritySettings
    from .mcp_server import mcp as fmcp
    # path="/" so that mounting at /mcp serves POST /mcp (redirect-free)
    # Allow tunnel/proxied hosts in the Host header (DNS rebinding protection kept on,
    # with an explicit allowlist).
    _allowed_hosts = [
        h.strip()
        for h in os.environ.get("MCP_ALLOWED_HOSTS", "127.0.0.1:8100,localhost:8100,secops-api.iman.qzz.io").split(",")
        if h.strip()
    ]
    mcp_app = fmcp.streamable_http_app(
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=_allowed_hosts,
            allowed_origins=[
                "https://secops-hub.iman.qzz.io",
                "http://localhost:5290",
                "http://127.0.0.1:5290",
            ],
        ),
    )
    HAS_MCP = True
except Exception:  # mcp not installed or failed to init
    HAS_MCP = False


@asynccontextmanager
async def lifespan(app):
    run_seed()
    import asyncio
    import os

    from .fetchers.nvd import sync_nvd
    from .database import SessionLocal

    interval = int(os.environ.get("SYNC_INTERVAL_MINUTES", "0"))
    auto_task = None

    async def auto_sync():
        while True:
            await asyncio.sleep(interval * 60)
            db = SessionLocal()
            try:
                sync_nvd(db, days=1, max_results=300)
            except Exception:
                pass
            finally:
                db.close()

    if interval > 0:
        auto_task = asyncio.create_task(auto_sync())

    session_ctx = None
    if HAS_MCP:
        session_ctx = fmcp.session_manager.run()
        await session_ctx.__aenter__()
    try:
        yield
    finally:
        if session_ctx:
            await session_ctx.__aexit__(None, None, None)
        if auto_task:
            auto_task.cancel()


app = FastAPI(title="SecOps Hub", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5290", "http://127.0.0.1:5290",
        "https://secops-hub.iman.qzz.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if HAS_MCP:
    app.mount("/mcp", mcp_app)

from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from starlette.types import Scope  # noqa: E402

from .routers import (agents, alerts, ai, assets, auth_users, intel, kb,  # noqa: E402
                      mcpservers, report, scans, sessions, skills, stats, sync, vulns)

app.include_router(auth_users.router)
app.include_router(assets.router)
app.include_router(vulns.router)
app.include_router(intel.router)
app.include_router(scans.router)
app.include_router(ai.router)
app.include_router(stats.router)
app.include_router(sync.router)
app.include_router(agents.router)
app.include_router(mcpservers.router)
app.include_router(skills.router)
app.include_router(kb.router)
app.include_router(sessions.router)
app.include_router(alerts.router)
app.include_router(report.router)

# ---- global auth gate: /api/** requires login except /api/auth/login ----
PUBLIC_PATHS = {"/api/auth/login", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def auth_gate(request, call_next):
    path = request.url.path
    if (path.startswith("/api")
            and path not in PUBLIC_PATHS
            and not path.startswith("/api/auth")):
        from .auth import current_user  # lazy import
        try:
            # validate token without db-dependent user lookup failing loudly
            scope_auth = request.headers.get("Authorization", "")
            token = scope_auth.removeprefix("Bearer ").strip()
            from .auth import _SESSIONS
            import time as _time
            info = _SESSIONS.get(token)
            if not info or info["exp"] < _time.time():
                return JSONResponse({"detail": "未登录或登录已过期"}, status_code=401)
        except Exception:
            return JSONResponse({"detail": "未登录"}, status_code=401)
    return await call_next(request)


@app.get("/")
def root():
    return {"service": "SecOps Hub", "docs": "/docs", "mcp": "/mcp" if HAS_MCP else "disabled"}
