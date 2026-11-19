# SecOps Hub · 单位安全运营综合平台

面向单位内网安全工作的一站式自托管平台，通过调研并整合多个优秀开源安全项目的设计而成。

**技术栈：** FastAPI + SQLAlchemy (SQLite) + fastmcp（后端，同端口挂载 `/mcp` streamable HTTP MCP）· Vite + React 18（前端）

> 项目调研与设计分析见 [ANALYSIS.md](./ANALYSIS.md)。

## 功能模块

| 模块 | 能力 |
|---|---|
| 安全态势 | KPI 总览、严重级别分布、漏洞披露趋势、高危风险 TOP、最新情报 |
| 资产管理 | 域名/IP/应用台账、ICP 备案、互联网暴露面、关键性分级、技术指纹；多维资产画像（指纹 × 匹配漏洞 × 风险评分，借鉴 ARL-Next） |
| 漏洞库 | CVE / CNVD / CNNVD 归一管理、POC 与在野利用跟踪、资产指纹匹配预警、处置状态流转 |
| 威胁情报 | 多源聚合（CNNVD/CNVD/NVD/360CERT/奇安信/绿盟/OSCS），情报-漏洞库关联（借鉴 threat-broadcast）；**NVD API 2.0 实时同步**（CPE/CNA 指纹提取）、CIRCL 备用源、CNVD/CNNVD 批量 JSON 导入、可选定时自动同步 |
| 扫描任务 | 任务编排与引擎适配层；**真实 Nuclei 引擎接入**（自动检测 `NUCLEI_PATH`/PATH，JSONL 结果解析，未安装自动回退模拟引擎）、发现-复核闭环（确认/误报，借鉴 Shannon「无 PoC 不报告」） |
| AI 值守助手 | 漏洞研判简报与问答；可插拔 OpenAI 兼容 LLM（或本地 Ollama），无 Key 自动降级为规则引擎兜底 |
| MCP 接口 | 平台自身 MCP Server（mcp SDK streamable HTTP，同端口 `/mcp`）：`get_asset_profile` / `search_vulnerabilities` / `latest_intel` |
| 智能体平台（AgentScope） | 创建不同职责的智能体（AgentScope ReActAgent 运行时），每个智能体可配置绑定 **MCP 服务器 / Skills 技能包 / 知识库**，并拥有独立会话；消息持久化，工具调用过程可审计 |
| MCP 管理 | 内置平台接口 + 第三方注册（stdio / streamable-http），连通测试与工具清单 |
| Skills 管理 | 内置技能（资产/漏洞/情报查询、NVD 同步、KB 检索）+ 第三方上传（定义 `tool_*` 函数的 python 代码）+ **Hub 市场**（内置演示目录；配置 `SKILL_HUB_URL` 接入远程 Hub，支持安装/更新） |
| 知识库管理 | 多知识库、文档上传（文件/粘贴）、自动分块、检索测试；离线关键词检索，无需外部服务，智能体绑定后获得专用检索工具 |

## 快速开始

依赖：Python 3.11+（[uv](https://docs.astral.sh/uv/)）、Node 18+

```bash
# 后端（8100 端口；MCP 在 http://127.0.0.1:8100/mcp）
cd backend
uv sync
uv run uvicorn app.main:app --port 8100

# 前端（5290 端口，/api 与 /mcp 自动代理到后端）
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5290

### 数据源同步

| 数据源 | 模式 | 说明 |
|---|---|---|
| NVD (NIST) | 实时 API 2.0 | `POST /api/sync/nvd?days=7&max_results=200`，无 Key 限速 5 次/30 秒；配置 `NVD_API_KEY` 提速。自动从 CNA `affected`/CPE 提取产品关键词用于资产匹配 |
| CIRCL CVE | 实时 API | `POST /api/sync/circl`，备用源（最近 30 条新收录） |
| CNVD | 批量导入 | 无公开 API——用单位账号在 cnvd.org.cn 导出增量文件后 `POST /api/sync/import`（JSON 列表或 `{"records":[...]}`） |
| CNNVD | 批量导入 | API 需官方授权——导出文件后同样导入（传 `"source": "CNNVD"`） |

各源最近同步时间：`GET /api/sync/status`。定时自动同步：启动后端时设置环境变量 `SYNC_INTERVAL_MINUTES=120`（每 2 小时一次）。

### 可选：启用 LLM 模式

任意 OpenAI 兼容接口，包括完全本地化的 Ollama（数据不出网）：

```bash
export LLM_API_BASE=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=qwen2.5:7b
```

未配置时 AI 助手自动降级为规则引擎应答，平台功能不受影响。`backend/mock_llm.py` 提供了一个用于联调测试的 OpenAI 兼容流式 LLM 桩（`python mock_llm.py 8399`，配合 `LLM_API_BASE=http://127.0.0.1:8399/v1 LLM_API_KEY=mock LLM_MODEL=mock-model` 启动后端即可真跑 AgentScope 链路）。

### 技能 Hub

`SKILL_HUB_URL` 指向任意静态托管目录，提供 `{HUB_URL}/index.json` 与技能 manifest（`{"name","version","description","code"}`，code 内定义 `tool_*` 函数）。未配置时使用内置演示目录（漏洞情报中文化、应急清单两个示例技能）。

### 已知事项

- 使用 **agentscope 2.x**（≥2.0.12，requires-python ≥3.11）+ **mcp 2.x**；平台 MCP Server 使用 mcp SDK 内置 `MCPServer`（mcp 2.x 中 FastMCP 已更名为 MCPServer）。agentscope 1.x 时代的手工补丁（audio None 防护、ToolResponse 包装）在 2.x 已不需要——v2 的 FunctionTool 自动将 str 返回值转换为 ToolChunk。
- 平台侧 MCP 工具通过 `_ReadOnlyMCPClient` 标记为只读，agent 运行时自动放行（v2 权限引擎默认对非只读 MCP 工具要求人工确认）。
- 自定义/Hub 技能代码由管理员上传后 exec 执行，请仅安装可信来源的技能包。

### MCP 客户端配置（Claude / WorkBuddy / Cursor 等）

```json
{
  "mcpServers": {
    "secops-hub": { "url": "http://127.0.0.1:8100/mcp" }
  }
}
```

## 设计原则（来自调研项目的共识）

1. **情报 × 资产**——漏洞情报必须与资产指纹匹配才有价值。
2. **无 PoC 不报告**——扫描发现须经人工复核确认后方可进入处置。
3. **AI 可审计、可降级**——每条 AI 输出标注生成模式；无外部 Key 也能完整使用。
4. **仅限授权范围**——扫描与 POC 验证必须限定在书面授权的资产范围内。

## 认证与角色

平台启用后所有 `/api/**` 接口需要登录（Bearer Token，12 小时有效），MCP 端点独立于登录体系，供程序对接。

| 角色 | 权限 |
|---|---|
| admin 管理员 | 全部权限 + 用户管理 + 资产删除 |
| analyst 分析员 | 漏洞处置、通报生成、资产增改、批量导入、扫描任务 |
| viewer 只读 | 仅查看 |

首次启动自动创建（请立即修改密码，或用环境变量 `ADMIN_PASSWORD` 覆盖）：

- `admin / Admin@2026` —— 管理员
- `analyst / Analyst@2026` —— 分析员
- `viewer / Viewer@2026` —— 只读

## 演进路线

- [x] NVD 实时增量同步 + CIRCL 备用源 + CNVD/CNNVD 导入通道
- [x] 真实 Nuclei 引擎接入（自动检测、JSONL 解析、回退机制）
- [x] 登录认证 + 三级角色（admin/analyst/viewer）+ 用户管理
- [x] 列表分页 + 资产 Excel/CSV 批量导入导出
- [x] 漏洞处置流转（状态 + 事件轨迹）+ Word 处置通报导出
- [x] 站内预警中心（高危/严重自动预警、处置后自动关闭）
- [x] AgentScope 智能体平台（MCP/Skills/知识库管理、多智能体独立会话）
- [x] 真实 LLM 接入验证（OpenAI 兼容网关，含推理模型思考标签清洗、agentscope 1.x ToolResponse 工具适配）
- [ ] Xray / GoPOC 引擎适配（poc-suite 引擎）
- [ ] 邮件与 IM 预警推送、通报 PDF 导出
- [ ] AI 建议与人工复核的签名审计台账（AiSOC 风格）
- [ ] LDAP/SSO 登录对接

## 许可证

MIT
