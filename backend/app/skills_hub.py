"""Skills Hub: remote index/download + builtin catalog sync.

Hub protocol (any static host works, e.g. GitHub raw / internal file server):
  {HUB_URL}/index.json -> [{"name": "...", "version": "...", "description": "...",
                            "url": "<absolute or relative url to skill manifest>"}]
  skill manifest -> {"name","version","description","code"}  (code defines tool_* functions)

Set SKILL_HUB_URL env to enable remote hub; a demo local hub catalog ships builtin.
"""
import json
import os

import httpx
from sqlalchemy.orm import Session

from .models import SkillItem

# Demo hub catalog served "locally" — content mirrors a real remote hub so the
# install flow is fully testable without an external server.
DEMO_HUB_INDEX = [
    {
        "name": "vuln-translator",
        "version": "1.2.0",
        "description": "漏洞情报中文化：将英文 CVE 描述翻译为中文并归纳处置要点",
        "url": "builtin://vuln-translator",
    },
    {
        "name": "incident-checklist",
        "version": "1.0.1",
        "description": "应急响应清单：按事件类型输出排查步骤与取证要点",
        "url": "builtin://incident-checklist",
    },
]

DEMO_HUB_MANIFESTS = {
    "vuln-translator": {
        "name": "vuln-translator",
        "version": "1.2.0",
        "description": "漏洞情报中文化：将英文 CVE 描述翻译为中文并归纳处置要点",
        "code": '''

def tool_translate_vuln(title: str, summary: str) -> str:
    """将英文漏洞标题与摘要中文化，输出：中文名称、风险要点、处置建议三段。

    Args:
        title (str): 英文漏洞标题。
        summary (str): 英文漏洞摘要描述。
    """
    return (
        f"中文名称：{title}\\n"
        f"风险要点：{summary[:300]}\\n"
        f"处置建议：请结合受影响产品官方补丁与访问控制措施进行处置，"
        f"高危及以上须在 72 小时内完成。"
    )
''',
    },
    "incident-checklist": {
        "name": "incident-checklist",
        "version": "1.0.1",
        "description": "应急响应清单：按事件类型输出排查步骤与取证要点",
        "code": '''

def tool_incident_checklist(event_type: str) -> str:
    """输出指定类型的应急响应排查清单。

    Args:
        event_type (str): 事件类型，如 勒索 / webshell / 钓鱼邮件 / 数据泄露。
    """
    base = "1) 隔离受影响主机；2) 保留内存与磁盘镜像取证；3) 排查横向移动痕迹；"
    extra = {
        "勒索": "4) 确认加密范围与备份可用性；5) 排查初始入侵点（RDP/VPN 弱口令）。",
        "webshell": "4) 全盘扫描 webshell 并比对文件哈希；5) 审查 web 日志定位上传路径。",
        "钓鱼邮件": "4) 在邮件网关召回同主题邮件；5) 排查是否有点击与凭据泄露。",
        "数据泄露": "4) 确认泄露数据范围与流向；5) 评估通报义务并留存证据。",
    }
    return base + extra.get(event_type, "4) 按通用流程排查并上报值班负责人。")
''',
    },
}


def hub_index() -> dict:
    """Fetch hub index: remote (SKILL_HUB_URL) if set, else demo catalog."""
    url = os.environ.get("SKILL_HUB_URL", "").rstrip("/")
    if url:
        try:
            resp = httpx.get(f"{url}/index.json", timeout=30)
            resp.raise_for_status()
            return {"ok": True, "hub": url, "skills": resp.json()}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": f"Hub 请求失败: {exc}", "skills": []}
    return {"ok": True, "hub": "builtin-demo", "skills": DEMO_HUB_INDEX}


def install_from_hub(db: Session, name: str, manifest: dict) -> dict:
    """Upsert a skill from a hub manifest (code mirrored to server file
    by the router after commit)."""
    if not manifest.get("code"):
        return {"ok": False, "error": "manifest 缺少 code 字段"}
    row = db.query(SkillItem).filter(SkillItem.name == name).first()
    if row:
        row.version = manifest.get("version", row.version)
        row.description = manifest.get("description", row.description)
        row.code = manifest["code"]
        row.source = "hub"
        action = "updated"
    else:
        db.add(SkillItem(name=name, version=manifest.get("version", "1.0.0"),
                         source="hub", description=manifest.get("description", ""),
                         code=manifest["code"]))
        action = "installed"
    db.commit()
    return {"ok": True, "action": action, "name": name, "version": manifest.get("version", "")}


def resolve_manifest(name: str, url: str) -> dict:
    """Fetch a skill manifest from hub url (http) or the demo catalog (builtin://)."""
    if url.startswith("builtin://"):
        m = DEMO_HUB_MANIFESTS.get(name)
        if not m:
            return {"ok": False, "error": f"demo hub 中不存在 {name}"}
        return {"ok": True, "manifest": m}
    base = os.environ.get("SKILL_HUB_URL", "").rstrip("/")
    target = url if url.startswith("http") else f"{base}/{url.lstrip('/')}"
    try:
        resp = httpx.get(target, timeout=30)
        resp.raise_for_status()
        return {"ok": True, "manifest": resp.json()}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"下载失败: {exc}"}
