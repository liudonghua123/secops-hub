import { useState } from "react";
import { api, setAuth } from "../api.js";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (!username || !password) {
      setErr("请输入用户名和密码");
      return;
    }
    setBusy(true);
    try {
      const r = await api.login(username, password);
      setAuth(r.token, r.user);
      onLogin(r.user);
    } catch (ex) {
      setErr(ex.message || "登录失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="login-island" onSubmit={submit}>
        <div className="brand" style={{ justifyContent: "center", paddingBottom: 8 }}>
          <div className="brand-logo">SH</div>
          <div>
            <div className="brand-title">SecOps Hub</div>
            <div className="brand-sub">单位安全运营综合平台</div>
          </div>
        </div>
        <label className="login-field">
          <span>用户名</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus placeholder="admin" />
        </label>
        <label className="login-field">
          <span>密码</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </label>
        {err && <div className="login-error">{err}</div>}
        <button type="submit" disabled={busy} style={{ width: "100%", marginTop: 4 }}>
          {busy ? "登录中…" : "登录"}
        </button>
        <div className="login-hint">
          初始账号：admin / Admin@2026（管理员）· analyst / Analyst@2026（分析员）· viewer / Viewer@2026（只读）
          <br />首次登录后请立即修改密码
        </div>
      </form>
    </div>
  );
}
