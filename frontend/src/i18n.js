// Lightweight i18n: zh (default) / en. Strings resolved via t(key).
import { useEffect, useState } from "react";

const LS_KEY = "secops_lang";

const DICT = {
  // ---- app shell ----
  "app.name": { zh: "SecOps Hub", en: "SecOps Hub" },
  "app.sub": { zh: "单位安全运营综合平台", en: "Security Operations Platform" },
  "nav.dashboard": { zh: "安全态势", en: "Dashboard" },
  "nav.assets": { zh: "资产管理", en: "Assets" },
  "nav.vulns": { zh: "漏洞库", en: "Vulnerabilities" },
  "nav.intel": { zh: "威胁情报", en: "Threat Intel" },
  "nav.scans": { zh: "扫描任务", en: "Scans" },
  "nav.ai": { zh: "AI 值守助手", en: "AI Assistant" },
  "nav.agents": { zh: "智能体", en: "Agents" },
  "nav.mcp": { zh: "MCP 管理", en: "MCP Servers" },
  "nav.skills": { zh: "Skills 管理", en: "Skills" },
  "nav.kb": { zh: "知识库", en: "Knowledge Base" },
  "nav.users": { zh: "用户与权限", en: "Users & Roles" },
  "foot.notice": { zh: "数据仅限本单位授权范围使用", en: "Data is restricted to authorized use" },
  "foot.confirm": { zh: "扫描与处置动作需人工确认", en: "Scan & disposal need manual confirmation" },
  "foot.mcp": { zh: "MCP 接口：/mcp (streamable HTTP)", en: "MCP endpoint: /mcp (streamable HTTP)" },
  "top.alerts": { zh: "预警中心", en: "Alert Center" },
  "top.markAll": { zh: "全部已读", en: "Mark all read" },
  "top.noAlerts": { zh: "暂无预警。高危/严重漏洞入库后会自动提醒。", en: "No alerts. Critical/high vulns trigger reminders." },
  "top.read": { zh: "已读", en: "Read" },
  "top.logout": { zh: "退出", en: "Logout" },
  "top.menu": { zh: "菜单", en: "Menu" },
  "role.admin": { zh: "管理员", en: "Admin" },
  "role.analyst": { zh: "分析员", en: "Analyst" },
  "role.viewer": { zh: "只读", en: "Viewer" },

  // ---- login ----
  "login.title": { zh: "登录", en: "Sign in" },
  "login.user": { zh: "用户名", en: "Username" },
  "login.pass": { zh: "密码", en: "Password" },
  "login.doing": { zh: "登录中…", en: "Signing in…" },
  "login.need": { zh: "请输入用户名和密码", en: "Username and password required" },
  "login.hint": {
    zh: "初始账号：admin / Admin@2026（管理员）· analyst / Analyst@2026（分析员）· viewer / Viewer@2026（只读）",
    en: "Default accounts: admin / Admin@2026 (Admin) · analyst / Analyst@2026 (Analyst) · viewer / Viewer@2026 (Read-only)",
  },
  "login.hint2": { zh: "首次登录后请立即修改密码", en: "Change the password right after first login" },

  // ---- common ----
  "c.save": { zh: "保存", en: "Save" },
  "c.cancel": { zh: "取消", en: "Cancel" },
  "c.delete": { zh: "删除", en: "Delete" },
  "c.edit": { zh: "编辑", en: "Edit" },
  "c.view": { zh: "查看", en: "View" },
  "c.search": { zh: "检索", en: "Search" },
  "c.collapse": { zh: "收起", en: "Collapse" },
  "c.none": { zh: "暂无", en: "None" },
  "c.confirmDelete": { zh: "确认删除？", en: "Confirm delete?" },

  // ---- theme ----
  "theme.auto": { zh: "自动", en: "Auto" },
  "theme.light": { zh: "浅色", en: "Light" },
  "theme.dark": { zh: "深色", en: "Dark" },

  // ---- kb ----
  "kb.title": { zh: "知识库管理", en: "Knowledge Base" },
  "kb.desc": {
    zh: "以库/目录形式组织制度、预案与设备资料，支持目录树、批量上传，自动分块供智能体检索",
    en: "Organize playbooks & documents as libraries with folder trees, batch upload, auto chunking for agent retrieval",
  },
  "kb.new": { zh: "新建知识库", en: "New Library" },
  "kb.name": { zh: "知识库名称", en: "Library name" },
  "kb.descLabel": { zh: "描述", en: "Description" },
  "kb.create": { zh: "创建", en: "Create" },
  "kb.noKb": { zh: "暂无知识库", en: "No libraries yet" },
  "kb.docs": { zh: "个文档", en: " docs" },
  "kb.folders": { zh: "个目录", en: " folders" },
  "kb.newFolder": { zh: "新建目录", en: "New folder" },
  "kb.folderName": { zh: "目录名，如 预案/网络", en: "Folder path, e.g. playbooks/net" },
  "kb.upload": { zh: "上传文件（可多选）", en: "Upload files (multi)" },
  "kb.paste": { zh: "或粘贴文本", en: "or paste text" },
  "kb.filename": { zh: "文件名", en: "Filename" },
  "kb.pasteIn": { zh: "入库", en: "Add to library" },
  "kb.delKb": { zh: "删除知识库", en: "Delete library" },
  "kb.delKbConfirm": { zh: "删除整个知识库及其所有文档？", en: "Delete the whole library and all documents?" },
  "kb.tree": { zh: "目录树", en: "Folder tree" },
  "kb.noDocs": { zh: "暂无文档", en: "No documents" },
  "kb.pickKb": { zh: "左侧选择一个知识库管理文档", en: "Pick a library on the left to manage documents" },
  "kb.added": { zh: "已入库", en: "Added" },
  "kb.chunks": { zh: "个片段", en: " chunks" },
  "kb.uploadFail": { zh: "上传失败：", en: "Upload failed: " },
  "kb.results": { zh: "检索结果", en: "Search results" },
  "kb.noHits": { zh: "无匹配片段", en: "No matching chunks" },
  "kb.test": { zh: "检索测试…", en: "Search test…" },
  "kb.deleteFolder": { zh: "删除目录及其内容", en: "Delete folder & contents" },
  "kb.emptyFolder": { zh: "（空目录）", en: "(empty folder)" },
  "kb.nameRequired": { zh: "名称必填", en: "Name required" },
  "kb.fileAndContent": { zh: "文件名与内容必填", en: "Filename and content required" },

  // ---- skills ----
  "sk.title": { zh: "Skills 技能管理", en: "Skills" },
  "sk.desc": {
    zh: "内置技能 + 自定义上传 + Hub 下载；技能以 python 文件形式保存在服务器，可在线查看与编辑",
    en: "Builtin + custom upload + Hub download; skills persist as python files on the server, viewable & editable online",
  },
  "sk.hub": { zh: "Hub 市场", en: "Hub" },
  "sk.upload": { zh: "上传技能", en: "Upload Skill" },
  "sk.name": { zh: "技能名称", en: "Skill name" },
  "sk.version": { zh: "版本", en: "Version" },
  "sk.submit": { zh: "提交", en: "Submit" },
  "sk.col.skill": { zh: "技能", en: "Skill" },
  "sk.col.version": { zh: "版本", en: "Version" },
  "sk.col.source": { zh: "来源", en: "Source" },
  "sk.col.desc": { zh: "说明", en: "Description" },
  "sk.col.status": { zh: "状态", en: "Status" },
  "sk.col.actions": { zh: "操作", en: "Actions" },
  "sk.builtin": { zh: "内置", en: "Builtin" },
  "sk.custom": { zh: "自定义", en: "Custom" },
  "sk.enabled": { zh: "启用", en: "Enabled" },
  "sk.disabled": { zh: "停用", en: "Disabled" },
  "sk.builtinNote": { zh: "随平台内置", en: "Ships with platform" },
  "sk.codeTitle": { zh: "技能代码", en: "Skill code" },
  "sk.saved": { zh: "已保存", en: "Saved" },
  "sk.delConfirm": { zh: "删除该技能？", en: "Delete this skill?" },
  "sk.installing": { zh: "安装中...", en: "Installing..." },
  "sk.installed": { zh: "安装成功", en: "installed" },
  "sk.updated": { zh: "已更新", en: "updated" },
  "sk.failed": { zh: "失败：", en: "Failed: " },
  "sk.uploadFail": { zh: "上传失败：", en: "Upload failed: " },
  "sk.nameCodeRequired": { zh: "名称与代码必填", en: "Name and code required" },
  "sk.hubDemo": { zh: "内置演示目录 · 配置 SKILL_HUB_URL 接入远程 Hub", en: "Builtin demo catalog · set SKILL_HUB_URL for remote hub" },
  "sk.updateBtn": { zh: "更新", en: "Update" },
  "sk.installBtn": { zh: "安装", en: "Install" },
  "sk.alreadyV": { zh: "已装", en: "installed" },

  // ---- mcp ----
  "mcp.title": { zh: "MCP 服务器管理", en: "MCP Servers" },
  "mcp.desc": {
    zh: "内置平台接口（/mcp）+ 第三方 MCP（stdio / streamable-http），供智能体绑定调用",
    en: "Built-in platform endpoint (/mcp) + third-party MCP (stdio / streamable-http) for agent binding",
  },
  "mcp.register": { zh: "注册服务器", en: "Register server" },
  "mcp.name": { zh: "名称", en: "Name" },
  "mcp.note": { zh: "备注", en: "Note" },
  "mcp.test": { zh: "连通测试", en: "Test" },
  "mcp.testing": { zh: "测试中...", en: "Testing..." },
  "mcp.delConfirm": { zh: "删除该 MCP 服务器注册？", en: "Delete this MCP server registration?" },
  "mcp.col.transport": { zh: "传输", en: "Transport" },
  "mcp.col.addr": { zh: "地址/命令", en: "Address/Command" },
  "mcp.col.status": { zh: "状态", en: "Status" },
  "mcp.col.tools": { zh: "工具数", en: "Tools" },
  "mcp.col.note": { zh: "备注", en: "Note" },
  "mcp.col.actions": { zh: "操作", en: "Actions" },
  "mcp.none": {
    zh: "尚未注册 MCP 服务器。可把平台自身（http://127.0.0.1:8100/mcp/）注册进来供智能体调用。",
    en: "No MCP servers registered. Register the platform itself (http://127.0.0.1:8100/mcp/) for agent use.",
  },
  "mcp.ok": { zh: "连通", en: "Reachable" },
  "mcp.fail": { zh: "失败：", en: "Failed: " },
  "mcp.tools": { zh: "个工具", en: " tools: " },

  // ---- misc levels ----
  "level.crit": { zh: "严重", en: "Critical" },
  "level.high": { zh: "高危", en: "High" },
  "level.mid": { zh: "中危", en: "Medium" },
  "level.low": { zh: "低危", en: "Low" },
};

function detect() {
  const saved = localStorage.getItem(LS_KEY);
  if (saved === "en" || saved === "zh") return saved;
  // auto: follow browser language, default zh
  const nav = (navigator.language || "zh").toLowerCase();
  return nav.startsWith("zh") ? "zh" : "en";
}

const listeners = new Set();

export function getLang() {
  const [lang, setLang] = useState(detect());
  useEffect(() => {
    const fn = (l) => setLang(l);
    listeners.add(fn);
    return () => listeners.delete(fn);
  }, []);
  return lang;
}

export function setLang(lang) {
  localStorage.setItem(LS_KEY, lang);
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  listeners.forEach((fn) => fn(lang));
}

// Eagerly sync <html lang> on module load
document.documentElement.lang = detect() === "zh" ? "zh-CN" : "en";

export function t(key, lang) {
  const l = lang || (typeof window !== "undefined" && localStorage.getItem(LS_KEY)) || "zh";
  const entry = DICT[key];
  if (!entry) return key;
  return entry[l] || entry.zh || key;
}

// Hook: re-render on language change
export function useT() {
  const lang = getLang();
  return (key) => t(key, lang);
}
