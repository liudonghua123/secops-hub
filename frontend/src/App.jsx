import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, clearAuth, getStoredUser } from "./api.js";
import { setLang, useT } from "./i18n.js";
import { useTheme } from "./theme.js";
import Dashboard from "./pages/Dashboard.jsx";
import Assets from "./pages/Assets.jsx";
import Vulns from "./pages/Vulns.jsx";
import Intel from "./pages/Intel.jsx";
import Scans from "./pages/Scans.jsx";
import AIChat from "./pages/AIChat.jsx";
import Agents from "./pages/Agents.jsx";
import AgentChat from "./pages/AgentChat.jsx";
import Mcp from "./pages/Mcp.jsx";
import Skills from "./pages/Skills.jsx";
import Kb from "./pages/Kb.jsx";
import Login from "./pages/Login.jsx";
import Alerts from "./pages/Alerts.jsx";
import Users from "./pages/Users.jsx";

const ICONS = {
  dashboard: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>,
  assets: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h4M6 14h8"/></svg>,
  vulns: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 3l9 4v5c0 5-3.8 8.4-9 9-5.2-.6-9-4-9-9V7z"/><path d="M12 9v4M12 16v.5"/></svg>,
  intel: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.5"/></svg>,
  scans: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>,
  ai: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="4" y="7" width="16" height="11" rx="3"/><path d="M12 7V4M8 12h.5M15.5 12h.5M9 15h6"/></svg>,
  agents: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="12" cy="18" r="3"/><path d="M6 9v3a3 3 0 003 3h6a3 3 0 003-3V9M9 15l-1.5 3M15 15l1.5 3"/></svg>,
  mcp: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.5M7 16.5h.5"/></svg>,
  skills: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7l8-4 8 4-8 4z"/><path d="M4 12l8 4 8-4M4 17l8 4 8-4"/></svg>,
  kb: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19V5a2 2 0 012-2h13v18H6a2 2 0 01-2-2zM8 7h8M8 11h8M8 15h5"/></svg>,
  bell: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 9a6 6 0 10-12 0c0 6-2 7-2 7h16s-2-1-2-7M10.3 20a2 2 0 003.4 0"/></svg>,
  users: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4a3.5 3.5 0 010 7M21.5 20c0-2.8-1.8-4.8-4.3-5.6"/></svg>,
  menu: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg>,
  sun: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>,
  moon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.8A9 9 0 1111.2 3 7 7 0 0021 12.8z"/></svg>,
  monitor: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>,
  globe: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 010 18M12 3a15 15 0 000 18"/></svg>,
  chevR: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 6l6 6-6 6"/></svg>,
};

// shadcn-admin style grouped nav
const NAV_GROUPS = [
  {
    titleKey: "nav.group.overview",
    items: [{ to: "/", key: "nav.dashboard", icon: "dashboard" }],
  },
  {
    titleKey: "nav.group.operations",
    items: [
      { to: "/assets", key: "nav.assets", icon: "assets" },
      { to: "/vulns", key: "nav.vulns", icon: "vulns" },
      { to: "/intel", key: "nav.intel", icon: "intel" },
      { to: "/scans", key: "nav.scans", icon: "scans" },
    ],
  },
  {
    titleKey: "nav.group.intelligence",
    items: [
      { to: "/ai", key: "nav.ai", icon: "ai" },
      { to: "/agents", key: "nav.agents", icon: "agents" },
      { to: "/mcp", key: "nav.mcp", icon: "mcp" },
      { to: "/skills", key: "nav.skills", icon: "skills" },
      { to: "/kb", key: "nav.kb", icon: "kb" },
    ],
  },
];

const THEME_ORDER = ["auto", "light", "dark"];
const THEME_ICON = { auto: "monitor", light: "sun", dark: "moon" };

function ThemeToggle() {
  const [theme, setThemeState] = useTheme();
  const t = useT();
  const next = () => setThemeState(THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % 3]);
  return (
    <button className="icon-btn" onClick={next} title={`${t("theme." + theme)} — ${t("theme.auto")}/${t("theme.light")}/${t("theme.dark")}`}>
      {ICONS[THEME_ICON[theme]]}
    </button>
  );
}

function LangToggle() {
  return (
    <button className="icon-btn" onClick={() => setLang(document.documentElement.lang.startsWith("zh") ? "en" : "zh")} title="中文 / English">
      {ICONS.globe}
    </button>
  );
}

// breadcrumb from current route
function Breadcrumb({ t }) {
  const { pathname } = useLocation();
  const flat = NAV_GROUPS.flatMap((g) => g.items);
  const cur = flat.find((i) => i.to === pathname);
  return (
    <div className="breadcrumb">
      <span className="crumb-root">{t("app.name")}</span>
      {cur && <>
        {ICONS.chevR}
        <span className="crumb-current">{t(cur.key)}</span>
      </>}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(getStoredUser());
  const [unread, setUnread] = useState(0);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const t = useT();

  // 401 时 api 层会广播此事件
  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener("secops:logout", onLogout);
    return () => window.removeEventListener("secops:logout", onLogout);
  }, []);

  const loadAlerts = () => {
    if (!user) return;
    api.alerts().then((d) => {
      setUnread(d.unread);
      setAlerts(d.items);
    }).catch(() => {});
  };
  useEffect(loadAlerts, [user]);
  useEffect(() => {
    if (!user) return;
    const iv = setInterval(loadAlerts, 60000);
    return () => clearInterval(iv);
  }, [user]);

  if (!user) return <Login onLogin={setUser} />;

  const doLogout = async () => {
    try { await api.logout(); } catch { /* ignore */ }
    clearAuth();
    setUser(null);
  };

  const markAll = async () => {
    await api.markAlerts([], true);
    loadAlerts();
  };

  const navClick = () => setMenuOpen(false);

  return (
    <>
      {menuOpen && <div className="drawer-mask" onClick={() => setMenuOpen(false)} style={{ zIndex: 49 }} />}
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-logo">SH</div>
          <div>
            <div className="brand-title">{t("app.name")}</div>
            <div className="brand-sub">{t("app.sub")}</div>
          </div>
        </div>
        <nav className="nav" onClick={navClick}>
          {NAV_GROUPS.map((g) => (
            <div key={g.titleKey}>
              <div className="nav-group-title">{t(g.titleKey)}</div>
              {g.items.map((n) => (
                <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? "active" : "")} end={n.to === "/"}>
                  {ICONS[n.icon]}
                  <span>{t(n.key)}</span>
                </NavLink>
              ))}
            </div>
          ))}
          {user.role === "admin" && (
            <>
              <div className="nav-group-title">{t("nav.group.admin")}</div>
              <NavLink to="/users" className={({ isActive }) => (isActive ? "active" : "")}>
                {ICONS.users}
                <span>{t("nav.users")}</span>
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-foot">
          {t("foot.notice")}<br />
          {t("foot.confirm")}<br />
          {t("foot.mcp")}
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <button className="icon-btn sidebar-toggle" onClick={() => setMenuOpen(!menuOpen)} title={t("top.menu")}>
            {ICONS.menu}
          </button>
          <Breadcrumb t={t} />
          <div className="spacer" />
          <ThemeToggle />
          <LangToggle />
          <button className="bell-btn" onClick={() => { setAlertOpen(!alertOpen); if (!alertOpen) loadAlerts(); }}>
            {ICONS.bell}
            {unread > 0 && <span className="bell-dot">{unread > 99 ? "99+" : unread}</span>}
          </button>
          {alertOpen && (
            <div className="alert-pop card">
              <div className="alert-pop-head">
                <strong>{t("top.alerts")}</strong>
                {unread > 0 && <button className="sm ghost" onClick={markAll}>{t("top.markAll")}</button>}
              </div>
              {alerts.length === 0 && <div className="page-desc" style={{ padding: "8px 4px" }}>{t("top.noAlerts")}</div>}
              {alerts.slice(0, 8).map((a) => (
                <div key={a.id} className={`alert-item ${a.read ? "" : "unread"}`}>
                  <span className={`tag tag-${a.level === "严重" ? "crit" : a.level === "高危" ? "high" : "mid"}`}>{a.level}</span>
                  <div className="alert-item-body">
                    <div className="li-title" style={{ cursor: a.ref_type === "vuln" ? "pointer" : "default" }}
                         onClick={() => { if (a.ref_type === "vuln") { navigate(`/vulns?v=${a.ref_id}`); setAlertOpen(false); } }}>
                      {a.title}
                    </div>
                    <div className="li-meta">{a.detail}</div>
                  </div>
                  {!a.read && <button className="sm ghost" onClick={() => api.markAlerts([a.id]).then(loadAlerts)}>{t("top.read")}</button>}
                </div>
              ))}
            </div>
          )}
          <div className="user-chip">
            <span className="user-avatar">{(user.display_name || user.username || "?").slice(0, 1)}</span>
            <span className="user-meta">
              <span className="user-name">{user.display_name}</span>
              <span className="user-role">{t("role." + user.role) || user.role}</span>
            </span>
            <button className="sm ghost" onClick={doLogout}>{t("top.logout")}</button>
          </div>
        </div>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/vulns" element={<Vulns />} />
          <Route path="/intel" element={<Intel />} />
          <Route path="/scans" element={<Scans />} />
          <Route path="/ai" element={<AIChat />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agent-chat/:agentId" element={<AgentChat />} />
          <Route path="/mcp" element={<Mcp />} />
          <Route path="/skills" element={<Skills />} />
          <Route path="/kb" element={<Kb />} />
          <Route path="/users" element={<Users />} />
        </Routes>
      </main>
    </>
  );
}
