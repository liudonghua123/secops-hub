"""ORM models for SecOps Hub."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(20), default="domain")  # domain/ip/app/host
    value: Mapped[str] = mapped_column(String(200), index=True)
    owner_dept: Mapped[str] = mapped_column(String(100), default="")
    criticality: Mapped[str] = mapped_column(String(10), default="中")  # 高/中/低
    icp_no: Mapped[str] = mapped_column(String(100), default="")
    exposure: Mapped[bool] = mapped_column(Boolean, default=False)  # 互联网暴露
    fingerprint: Mapped[str] = mapped_column(Text, default="")  # 技术栈指纹, 逗号分隔
    status: Mapped[str] = mapped_column(String(20), default="在用")
    last_scan_at: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cve_id: Mapped[str] = mapped_column(String(30), index=True, default="")
    cnnvd_id: Mapped[str] = mapped_column(String(30), index=True, default="")
    cnvd_id: Mapped[str] = mapped_column(String(30), index=True, default="")
    title: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(10), index=True)  # 严重/高危/中危/低危
    cvss: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(30), default="NVD")
    description: Mapped[str] = mapped_column(Text, default="")
    affected_keywords: Mapped[str] = mapped_column(Text, default="")  # 与资产指纹匹配的关键词
    poc_available: Mapped[bool] = mapped_column(Boolean, default=False)
    exploited_in_wild: Mapped[bool] = mapped_column(Boolean, default=False)
    fix_suggestion: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="未处置")  # 未处置/处置中/已修复
    published_at: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class IntelItem(Base):
    __tablename__ = "intel_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(30), index=True)  # CVE/CNNVD/CNVD/360CERT/QAX/NSFOCUS/OSCS
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(10), default="")
    ref_id: Mapped[str] = mapped_column(String(30), default="")  # CVE/CNVD 编号
    published_at: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ScanTask(Base):
    __tablename__ = "scan_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    target_scope: Mapped[str] = mapped_column(Text, default="")  # 目标范围描述
    engine: Mapped[str] = mapped_column(String(30), default="nuclei")  # nuclei/poc-suite/weak-pass
    status: Mapped[str] = mapped_column(String(20), default="待执行")  # 待执行/执行中/已完成
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    started_at: Mapped[str] = mapped_column(String(30), default="")
    finished_at: Mapped[str] = mapped_column(String(30), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentProfile(Base):
    """A configurable agent: model prompt + bound MCP servers / skills / knowledge bases."""
    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    sys_prompt: Mapped[str] = mapped_column(Text, default="你是单位网络安全值守助手。")
    model_name: Mapped[str] = mapped_column(String(100), default="")  # 空则用全局 LLM_MODEL
    mcp_ids: Mapped[str] = mapped_column(Text, default="[]")   # JSON list[int]
    skill_ids: Mapped[str] = mapped_column(Text, default="[]") # JSON list[int]
    kb_ids: Mapped[str] = mapped_column(Text, default="[]")    # JSON list[int]
    max_iters: Mapped[int] = mapped_column(Integer, default=10)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MCPServer(Base):
    """MCP server registry: builtin (this platform) or third-party (stdio/http)."""
    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    transport: Mapped[str] = mapped_column(String(20), default="http")  # stdio/http
    command: Mapped[str] = mapped_column(String(300), default="")  # stdio
    args: Mapped[str] = mapped_column(Text, default="[]")          # stdio, JSON list
    url: Mapped[str] = mapped_column(String(500), default="")      # http
    headers: Mapped[str] = mapped_column(Text, default="{}")       # http, JSON dict
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="未测试")  # 未测试/正常/失败
    tool_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SkillItem(Base):
    """Skill packs: builtin / uploaded custom / downloaded from hub."""
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    source: Mapped[str] = mapped_column(String(20), default="builtin")  # builtin/custom/hub
    description: Mapped[str] = mapped_column(String(500), default="")
    code: Mapped[str] = mapped_column(Text, default="")  # python 定义若干 @tool 函数
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(Integer, index=True)
    filename: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, default="")
    chunks: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(200), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(20))  # user/assistant/tool/system
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[str] = mapped_column(Text, default="")  # JSON: 工具调用等
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    """Platform user with role-based access."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    display_name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # admin/analyst/viewer
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VulnEvent(Base):
    """处置/流转 audit trail attached to a vulnerability."""
    __tablename__ = "vuln_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vuln_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(30))     # 状态变更/备注/通报生成
    detail: Mapped[str] = mapped_column(Text, default="")
    operator: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Alert(Base):
    """站内预警：高危/严重漏洞入库、扫描完成等自动生成。"""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(10), default="高危")  # 严重/高危/中危
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str] = mapped_column(Text, default="")
    ref_type: Mapped[str] = mapped_column(String(20), default="vuln")
    ref_id: Mapped[int] = mapped_column(Integer, default=0)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SyncState(Base):
    """Key-value store for per-source sync bookkeeping."""
    __tablename__ = "sync_state"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    asset_value: Mapped[str] = mapped_column(String(200))
    vuln_title: Mapped[str] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(10))
    poc_ref: Mapped[str] = mapped_column(String(100), default="")  # POC/CVE 编号
    evidence: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    false_positive: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
