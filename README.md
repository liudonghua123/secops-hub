# SecOps Hub

A comprehensive, self-hosted security operations platform for organizational (unit-level) cybersecurity work, built by studying and integrating ideas from outstanding open-source security projects.

**Stack:** FastAPI + SQLAlchemy (SQLite) + fastmcp (backend, MCP at `/mcp` on the same port) · Vite + React 18 (frontend)

> 调研分析报告见 [ANALYSIS.md](./ANALYSIS.md)，中文说明见 [README.zh_CN.md](./README.zh_CN.md)。

## Features

| Module | Capabilities |
|---|---|
| Security Overview | KPI dashboard, severity distribution, vulnerability trend, top risks, latest intel |
| Asset Management | Domain/IP/app inventory, ICP record, exposure flag, criticality, fingerprint; multi-dimension asset profile with matched vulnerabilities & risk score (inspired by ARL-Next) |
| Vulnerability Library | Unified CVE / CNVD / CNNVD records, POC availability & in-the-wild tracking, asset-fingerprint matching for early warning, disposition status workflow |
| Threat Intelligence | Multi-source aggregation (CNNVD/CNVD/NVD/360CERT/QAX/NSFOCUS/OSCS), intel-to-vulnerability linking (inspired by threat-broadcast); **live NVD API 2.0 sync** with CPE/CNA fingerprint extraction, CIRCL backup feed, CNVD/CNNVD batch JSON import, optional scheduled auto-sync |
| Scan Tasks | Task orchestration with engine adapter layer; **real Nuclei integration** (auto-detected via `NUCLEI_PATH`/PATH, JSONL findings parsing, graceful fallback to simulation when not installed), finding review loop: confirm / false-positive (inspired by Shannon's "no PoC, no report") |
| AI Assistant | Vulnerability briefing & Q&A; pluggable OpenAI-compatible LLM (or local Ollama) with rule-engine fallback when no key is configured |
| MCP Interface | Platform MCP server (mcp-SDK FastMCP, streamable HTTP at `/mcp`, same port): `get_asset_profile`, `search_vulnerabilities`, `latest_intel` |
| Agent Platform (AgentScope) | Create role-specific agents on the AgentScope ReActAgent runtime; each agent binds its own **MCP servers / skill packs / knowledge bases** and owns independent sessions with persisted messages |
| MCP Management | Register third-party MCP servers (stdio / streamable-http), live connect test with tool listing |
| Skills Management | Builtin skills (asset/vuln/intel queries, NVD sync, KB search) + third-party upload (python code defining `tool_*` functions) + **Skill Hub** (builtin demo catalog; set `SKILL_HUB_URL` for a remote hub, install/update supported) |
| Knowledge Base | Multiple KBs, document upload (file/paste), auto chunking, retrieval preview; offline keyword retrieval — bound agents get a dedicated search tool |

## Quick Start

Requirements: Python 3.11+ ([uv](https://docs.astral.sh/uv/)), Node 18+

```bash
# Backend (port 8100; MCP at http://127.0.0.1:8100/mcp)
cd backend
uv sync
uv run uvicorn app.main:app --port 8100

# Frontend (port 5290, proxies /api and /mcp to backend)
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5290

### Data source sync

| Source | Mode | How |
|---|---|---|
| NVD (NIST) | Live API 2.0 | `POST /api/sync/nvd?days=7&max_results=200` — no key needed (5 req/30 s); set `NVD_API_KEY` for higher limits. Extracts product/vendor keywords from CNA `affected` data and legacy CPE for asset matching |
| CIRCL CVE | Live API | `POST /api/sync/circl` — backup feed, last 30 published CVEs |
| CNVD | Batch import | No open API — export from cnvd.org.cn with a unit account, then `POST /api/sync/import` (JSON list or `{"records":[...]}`) |
| CNNVD | Batch import | API requires official authorization — export file, import the same way (set `"source": "CNNVD"`) |

Per-source last-sync status: `GET /api/sync/status`. Scheduled auto-sync: start the backend with `SYNC_INTERVAL_MINUTES=120` (e.g. every 2 hours).

### Optional: enable LLM mode

Any OpenAI-compatible endpoint, including a fully local Ollama (data never leaves the network):

```bash
export LLM_API_BASE=http://localhost:11434/v1   # or any OpenAI-compatible base
export LLM_API_KEY=ollama                       # dummy for local ollama
export LLM_MODEL=qwen2.5:7b
```

Without these, the AI assistant degrades to a deterministic rule engine — the platform remains fully usable. `backend/mock_llm.py` is a streaming OpenAI-compatible stub for integration testing (`python mock_llm.py 8399`).

### Skill Hub

Point `SKILL_HUB_URL` at any static host serving `{HUB_URL}/index.json` plus skill manifests (`{"name","version","description","code"}`; code defines `tool_*` functions). Without it a builtin demo catalog is used (two example skills installable/updateable).

### Known notes

- Uses **agentscope 2.x** (>=2.0.12, requires-python >=3.11) + **mcp 2.x**; the platform MCP server uses the `MCPServer` bundled in the mcp SDK v2 (FastMCP was renamed in mcp 2.x). The agentscope 1.x hand patches (audio None guard, ToolResponse wrapping) are no longer needed — v2's FunctionTool auto-converts str returns to ToolChunk.
- Platform-side MCP tools are marked read-only via `_ReadOnlyMCPClient` so the v2 permission engine auto-allows them (by default non-read-only MCP tools require user confirmation).
- Custom/hub skill code is exec'd after admin upload — only install trusted skill packs.

### MCP client config (e.g. Claude Desktop / WorkBuddy)

```json
{
  "mcpServers": {
    "secops-hub": {
      "url": "http://127.0.0.1:8100/mcp"
    }
  }
}
```

## Project Layout

```
secops-hub/
├── ANALYSIS.md          # research & design report (Chinese)
├── backend/
│   ├── pyproject.toml   # uv-managed (FastAPI + agentscope + mcp)
│   ├── mock_llm.py      # OpenAI-compatible streaming stub for integration tests
│   └── app/
│       ├── main.py      # FastAPI entry, mounts /mcp (same port), auth gate
│       ├── auth.py      # PBKDF2 + token sessions + RBAC
│       ├── models.py    # assets/vulns/intel/scans + agents/mcp/skills/kb/sessions/users/alerts
│       ├── ai_service.py# LLM chat/brief + reasoning-tag cleanup + rule fallback
│       ├── agent_runtime.py  # AgentScope ReActAgent build & chat execution
│       ├── skills_builtin.py # builtin skill catalog & tool functions
│       ├── skills_hub.py     # hub index / download / install
│       ├── kb_engine.py      # KB chunking & retrieval
│       ├── mcp_server.py     # platform MCP server (mcp-SDK FastMCP)
│       ├── nuclei.py         # real Nuclei engine adapter
│       ├── fetchers/         # NVD / CIRCL / CNVD import
│       └── routers/          # assets vulns intel scans ai stats sync auth_users
│                             # agents mcpservers skills kb sessions report alerts
└── frontend/
    └── src/pages/       # Dashboard / Assets / Vulns / Intel / Scans / AIChat
                         # Agents / AgentChat / Mcp / Skills / Kb
                         # Login / Alerts / Users
```

### Auth & roles

Once started, all `/api/**` endpoints require login (Bearer token, 12h); the MCP endpoint is separate for programmatic access.

| Role | Permissions |
|---|---|
| admin | everything + user management + asset deletion |
| analyst | vuln disposition, notifications, asset edits, batch import, scans |
| viewer | read-only |

Auto-created on first start (change immediately, or override with `ADMIN_PASSWORD`):
`admin / Admin@2026` · `analyst / Analyst@2026` · `viewer / Viewer@2026`

## Design Principles (learned from the surveyed projects)

1. **Intelligence x Assets** — raw intel is noise until matched against your asset fingerprints.
2. **No PoC, no report** — findings must be verified and human-reviewed before disposition.
3. **Auditable & degradable AI** — every AI output is labelled with its mode; rule engine keeps the platform usable without any external API.
4. **Authorization scope only** — scanning and POC verification must stay within explicitly authorized assets.

## Roadmap

- [x] Real NVD incremental fetcher + CIRCL backup feed + CNVD/CNNVD import channel
- [x] Real Nuclei engine integration (auto-detect, JSONL parsing, fallback)
- [x] Auth + RBAC + pagination + Word notifications + alert center
- [x] AgentScope agent platform (MCP/Skills/KB, multi-agent sessions)
- [x] Real-LLM validation (OpenAI-compatible gateway, reasoning-tag cleanup, agentscope 1.x ToolResponse tool adaptation)
- [ ] Xray / GoPOC engine adapters (poc-suite engine)
- [ ] Word/PDF briefing export, email & IM notifications
- [ ] Signed audit ledger for AI suggestions and human reviews (AiSOC-style)
- [ ] LDAP/SSO login, RBAC per department

## License

MIT
