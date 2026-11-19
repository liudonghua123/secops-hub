const BASE = "";
const TOKEN_KEY = "secops_token";
const USER_KEY = "secops_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}
export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function req(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(BASE + path, { ...opts, headers });
  if (resp.status === 401 && !path.startsWith("/api/auth/login")) {
    clearAuth();
    window.dispatchEvent(new Event("secops:logout"));
    throw new ApiError(401, "登录已过期，请重新登录");
  }
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep default */ }
    throw new ApiError(resp.status, detail);
  }
  return resp.json();
}

async function download(path) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(BASE + path, { headers });
  if (!resp.ok) throw new ApiError(resp.status, "下载失败");
  const blob = await resp.blob();
  const cd = resp.headers.get("Content-Disposition") || "";
  const m = cd.match(/filename=([^;]+)/);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = m ? decodeURIComponent(m[1]) : "download";
  a.click();
  URL.revokeObjectURL(url);
}

export const api = {
  // ---- auth ----
  login: (username, password) =>
    req("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => req("/api/auth/logout", { method: "POST" }),
  me: () => req("/api/auth/me"),
  users: () => req("/api/auth/users"),
  createUser: (d) => req("/api/auth/users", { method: "POST", body: JSON.stringify(d) }),
  updateUser: (id, d) => req(`/api/auth/users/${id}`, { method: "PUT", body: JSON.stringify(d) }),
  deleteUser: (id) => req(`/api/auth/users/${id}`, { method: "DELETE" }),
  // ---- alerts ----
  alerts: (onlyUnread = false) => req(`/api/alerts${onlyUnread ? "?only_unread=true" : ""}`),
  markAlerts: (ids = [], all = false) =>
    req("/api/alerts/read", { method: "POST", body: JSON.stringify({ ids, all }) }),
  // ---- report ----
  vulnDocx: (ids) => download("/api/report/vuln-docx"),
  vulnDocxPost: async (ids) => {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const resp = await fetch("/api/report/vuln-docx", {
      method: "POST", headers, body: JSON.stringify({ vuln_ids: ids }),
    });
    if (!resp.ok) throw new ApiError(resp.status, "通报生成失败");
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = ids.length > 1 ? "漏洞处置通报(合并).docx" : "漏洞处置通报.docx";
    a.click();
    URL.revokeObjectURL(url);
  },
  exportAssets: (format = "xlsx") => download(`/api/assets/export?format=${format}`),
  importAssets: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const headers = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch("/api/assets/import", { method: "POST", body: fd, headers }).then(async (r) => {
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new ApiError(r.status, b.detail || "导入失败");
      }
      return r.json();
    });
  },
  // ---- core ----
  stats: () => req("/api/stats/overview"),
  trend: () => req("/api/stats/trend"),
  topRisks: () => req("/api/stats/top-risks"),
  assets: (params = "") => req(`/api/assets${params}`),
  assetProfile: (id) => req(`/api/assets/${id}/profile`),
  createAsset: (data) => req("/api/assets", { method: "POST", body: JSON.stringify(data) }),
  deleteAsset: (id) => req(`/api/assets/${id}`, { method: "DELETE" }),
  vulns: (params = "") => req(`/api/vulns${params}`),
  vuln: (id) => req(`/api/vulns/${id}`),
  setVulnStatus: (id, status, note = "") =>
    req(`/api/vulns/${id}/status`, { method: "PUT", body: JSON.stringify({ status, note }) }),
  vulnBrief: (id) => req(`/api/ai/vuln-brief/${id}`),
  intel: (params = "") => req(`/api/intel${params}`),
  intelSources: () => req("/api/intel/sources"),
  relatedVulns: (id) => req(`/api/intel/${id}/related-vulns`),
  tasks: () => req("/api/scans"),
  engines: () => req("/api/scans/engines"),
  createTask: (data) => req("/api/scans", { method: "POST", body: JSON.stringify(data) }),
  startTask: (id) => req(`/api/scans/${id}/start`, { method: "POST" }),
  findings: (id) => req(`/api/scans/${id}/findings`),
  reviewFinding: (id, action, reviewer = "analyst") =>
    req(`/api/scans/findings/${id}/review`, { method: "PUT", body: JSON.stringify({ action, reviewer }) }),
  aiStatus: () => req("/api/ai/status"),
  aiChat: (question) => req("/api/ai/chat", { method: "POST", body: JSON.stringify({ question }) }),
  syncStatus: () => req("/api/sync/status"),
  syncNvd: (days = 7) => req("/api/sync/nvd", { method: "POST", body: JSON.stringify({ days, max_results: 200 }) }),
  syncCircl: () => req("/api/sync/circl", { method: "POST" }),
  syncImport: (records, source = "CNVD") =>
    req("/api/sync/import", { method: "POST", body: JSON.stringify({ records, source }) }),
  nucleiStatus: () => req("/api/scans/nuclei-status"),
  // ---- agent platform ----
  agents: () => req("/api/agents"),
  agentOptions: () => req("/api/agents/options"),
  createAgent: (d) => req("/api/agents", { method: "POST", body: JSON.stringify(d) }),
  updateAgent: (id, d) => req(`/api/agents/${id}`, { method: "PUT", body: JSON.stringify(d) }),
  deleteAgent: (id) => req(`/api/agents/${id}`, { method: "DELETE" }),
  mcpServers: () => req("/api/mcp"),
  createMcp: (d) => req("/api/mcp", { method: "POST", body: JSON.stringify(d) }),
  updateMcp: (id, d) => req(`/api/mcp/${id}`, { method: "PUT", body: JSON.stringify(d) }),
  deleteMcp: (id) => req(`/api/mcp/${id}`, { method: "DELETE" }),
  testMcp: (id) => req(`/api/mcp/${id}/test`, { method: "POST" }),
  skills: () => req("/api/skills"),
  uploadSkill: (d) => req("/api/skills/upload", { method: "POST", body: JSON.stringify(d) }),
  deleteSkill: (id) => req(`/api/skills/${id}`, { method: "DELETE" }),
  toggleSkill: (id) => req(`/api/skills/${id}/toggle`, { method: "PUT" }),
  hubIndex: () => req("/api/skills/hub"),
  hubInstall: (name, url) => req("/api/skills/hub/install", { method: "POST", body: JSON.stringify({ name, url }) }),
  kbs: () => req("/api/kb"),
  createKb: (d) => req("/api/kb", { method: "POST", body: JSON.stringify(d) }),
  deleteKb: (id) => req(`/api/kb/${id}`, { method: "DELETE" }),
  kbDocs: (id) => req(`/api/kb/${id}/docs`),
  addKbDoc: (id, d) => req(`/api/kb/${id}/docs`, { method: "POST", body: JSON.stringify(d) }),
  uploadKbDoc: (id, file) => {
    const fd = new FormData();
    fd.append("file", file);
    const headers = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(`/api/kb/${id}/docs/upload`, { method: "POST", body: fd, headers }).then(async (r) => {
      if (!r.ok) throw new ApiError(r.status, "上传失败");
      return r.json();
    });
  },
  deleteKbDoc: (kbId, docId) => req(`/api/kb/${kbId}/docs/${docId}`, { method: "DELETE" }),
  kbSearch: (id, q) => req(`/api/kb/${id}/search?q=${encodeURIComponent(q)}`),
  sessions: (agentId) => req(`/api/sessions?agent_id=${agentId}`),
  createSession: (agentId, title = "") =>
    req("/api/sessions", { method: "POST", body: JSON.stringify({ agent_id: agentId, title }) }),
  deleteSession: (id) => req(`/api/sessions/${id}`, { method: "DELETE" }),
  sessionMessages: (id) => req(`/api/sessions/${id}/messages`),
  sessionChat: (id, content) =>
    req(`/api/sessions/${id}/chat`, { method: "POST", body: JSON.stringify({ content }) }),
};
