# 开源安全项目调研分析报告

> 调研时间：2026-11-19 · 目标：为单位内网安全工作整合一款综合平台（SecOps Hub）

## 一、调研范围与方法

围绕「威胁情报 / 漏洞管理 / 资产管理（扫描、验证、POC、CVE·CNNVD·CNVD 更新）/ AI 分析」四个方向，检索 GitHub 及安全社区近两年的活跃开源项目，按「能力定位、技术栈、可借鉴点、许可证」进行横向对比。

## 二、重点项目盘点

### 1. 威胁情报（TI）方向

| 项目 | 技术栈 | 核心能力 | 可借鉴点 |
|---|---|---|---|
| **thalesgroup-cert/Watcher** (AGPL-3.0) | Django + React | AI 驱动的威胁情报平台：RSS 聚合 CERT-FR/CERT-EU/US-CERT 等，HuggingFace (flan-t5 + NER) 做情报摘要与 IOC 提取、每周 TOP5 趋势摘要、突发告警；恶意域名监控（dnstwist 变体、certstream 证书透明度、TLSH 模糊哈希）；信息泄露监控（Pastebin/GitHub/GitLab 等）；MISP/TheHive 同步 | AI 周报/摘要流水线；情报源聚合 + 去重归档思路 |
| **threat-broadcast** (Mr-xn/TachiuLam) | Python | 聚合 360 CERT、奇安信、绿盟、安全客、CNVD、CNNVD、NVD 等十余个情报源，邮件推送 + GitHub Page 播报 + SQLite 归档 | 国内情报源清单与抓取节奏；「每小时增量拉取 + 去重」模式 |
| **BugFor-Pings/DLV** | Flask + SQLite | 5 分钟粒度爬取 OSCS、安天、Tenable、MSRC 等平台，每日漏洞情报预警展示 | 多源情报展示页的极简落地方式 |

### 2. 资产测绘 / ASM 方向

| 项目 | 技术栈 | 核心能力 | 可借鉴点 |
|---|---|---|---|
| **ARL-Next**（owl234，ARL 重构版，GPL-3.0） | Python 3.13 + Vue 3.5 + MongoDB 7 + Nmap 7.95 + Nuclei | 企业资产关联（多类型 ICP：网站/APP/小程序/快应用）、子域/IP/端口/服务测绘、8800+ Web 指纹、敏感信息流式提取、CVE 情报跟踪、GitHub 泄露监控、**原生 MCP Server（get_asset_profile）** | 资产组多级组织；ICP 备案关联资产；「资产画像 13 维聚合」；MCP 暴露查询能力给 AI 客户端 |
| **ScopeSentry / QingScan / nemo_go** 等 | Go/Python | 分布式资产收集、30+ 扫描器粘合调度 | 「任务队列 + 引擎插件池」的调度抽象 |

### 3. 漏洞扫描 / POC 验证方向

| 项目 | 技术栈 | 核心能力 | 可借鉴点 |
|---|---|---|---|
| **taielab/YinVulnKiller** (Apache-2.0) | 4 引擎协同（Nuclei + Xray + GoPOC + YamlPOC） | 13054+ POC 规则、Worker Pool 并发、内网探测、弱口令检测、实时漏洞输出 | 多引擎 POC 规则池与并发架构 |
| **taielab/YinPocX** | Python + AI 多模态 | 将 Markdown 漏洞报告智能转换为 Nuclei YAML 模板，动态 Prompt 优化 + 自动语法验证 | **AI 生成 POC 模板**的工作流 |
| **Strix / Shannon**（Keygraph，25k+ star） | Claude Agent SDK 多智能体 | 侦察→漏洞分析→利用验证→报告四阶段编排；只报告有 PoC 证实的结果，误报率极低 | 「无 PoC 不报漏洞」的验证闭环理念；多 Agent 分工 |
| **PentestGPT** (MIT, 14k+ star, USENIX Sec 2024) | LLM + Docker 沙箱 | 渗透流程 Agent 化，支持 OpenAI/Anthropic/DeepSeek/Ollama 本地后端 | 多 LLM 后端可插拔、本地化合规 |
| **AI-VAPT / Polyscope** | Go / Node | recon→CVE 映射→利用预测→报告的一体化流水线 | 报告引擎的风险评分与整改建议结构 |

### 4. AI 安全运营（SOC）方向

| 项目 | 技术栈 | 核心能力 | 可借鉴点 |
|---|---|---|---|
| **AiSOC** (6k+ star, MIT) | Python + Ollama 本地 3B 模型 | 告警融合、LLM Agent 分诊、MITRE ATT&CK 调查、**签名审计台账（Investigation Ledger）**、无外部 API、自带 MCP Server | 全本地推理（合规）；AI 决策全链路可审计 |
| **multi-agent-soc** (CrewAI + llama3.1) | CrewAI + ChromaDB + Streamlit | 分诊/猎杀/取证/报告四 Agent + 人工审批闸门（HITL）+ 指标看板 | 人工复核队列设计；「Agent 初筛 + 人拍板」 |
| **CyberSecurity-Intelligence-Platform** | Python | 4-Agent 流水线对接 NVD API，规则引擎兜底、LLM 可升级，自动产出 MD/PDF 情报报告 | **规则引擎兜底 + LLM 增强**的降级策略；通报自动生成 |

## 三、共性结论

1. **数据源是地基**：成熟项目都做「多源聚合 + 增量拉取 + 去重归档」（threat-broadcast、DLV、Watcher、ARL-Next 高度一致）。
2. **资产是坐标系**：漏洞情报必须与资产指纹匹配才有价值（ARL-Next 的「CVE 情报 × 资产指纹」联动是最佳实践）。
3. **验证决定可信度**：Shannon/YinVulnKiller 证明「带 PoC 的结果才值得报告」，平台必须保留人工复核闸门。
4. **AI 要可审计、可降级**：AiSOC 的审计台账、multi-agent-soc 的人工闸门、CyberSecurity-Intelligence-Platform 的规则兜底，构成 AI 落地三原则：**可解释、可回滚、无 Key 也能跑**。
5. **MCP 成为 AI 集成标准接口**：ARL-Next、AiSOC 均原生提供 MCP Server，允许外部 Agent 安全地查询平台数据。

## 四、目标产品设计（SecOps Hub）

定位：**单位内安全团队的一站式工作台**——资产台账、漏洞情报预警、扫描与 POC 验证、AI 研判助手，模块互通。

```
┌────────────────────────────────────────────────────┐
│                   前端 React + Vite                  │
│  仪表盘 │ 资产管理 │ 漏洞库 │ 威胁情报 │ 扫描任务 │ AI助手 │
└───────────────────────┬────────────────────────────┘
                        │ REST API
┌───────────────────────┴────────────────────────────┐
│              后端 FastAPI + SQLite(SQLAlchemy)       │
│  assets / vulns / intel / scans / ai / stats 路由    │
│  ├─ 情报聚合器：CVE·CNNVD·CNVD·360CERT·奇安信…（增量+去重）│
│  ├─ 资产-漏洞匹配引擎：CPE/关键词 × 资产指纹           │
│  ├─ 扫描任务编排：Nuclei/POC 引擎适配层（预留插件）     │
│  ├─ AI 服务层：OpenAI 兼容接口，规则引擎兜底           │
│  └─ MCP Server（fastmcp，同端口 /mcp，streamable HTTP）│
└────────────────────────────────────────────────────┘
```

**借鉴映射**

| 目标模块 | 主要借鉴 | 落地方式 |
|---|---|---|
| 漏洞情报与预警 | threat-broadcast / ARL-Next | 多源 schema 统一归档 + 严重级别归一 + 资产指纹匹配预警 |
| 资产管理与测绘 | ARL-Next | 资产组/关键性分级/备案信息/暴露面标记 + 资产画像 |
| 扫描与 POC 验证 | YinVulnKiller / Shannon | 任务-发现-复核（确认/误报）闭环，引擎适配层预留 Nuclei 接入 |
| AI 分析助手 | AiSOC / CyberSecurity-Intelligence-Platform | 漏洞通报自动生成、问答研判；OpenAI 兼容 LLM 可插拔 + 规则引擎兜底（无 Key 可用） |
| MCP 接口 | ARL-Next / AiSOC | fastmcp 同端口 /mcp，暴露资产画像/漏洞检索/最新情报三工具 |

**合规边界**：扫描与 POC 验证仅限授权资产范围；AI 建议需人工确认后方可执行处置动作。

## 五、后续演进路线

1. 对接真实数据源：NVD API 2h 增量、CNNVD/CNVD 批量接口（需单位账号）、OSCS。
2. 接入 Nuclei 引擎执行真实扫描（当前为任务编排 + 模拟引擎）。
3. 接入本地 Ollama 实现全离线 AI 研判（数据不出网）。
4. 通报/周报自动导出（Word/PDF）、邮件与 IM 推送。
5. 审计台账：记录所有 AI 建议与人工复核动作。
