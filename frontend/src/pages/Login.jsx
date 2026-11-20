import { useState } from "react";
import { api, setAuth } from "../api.js";
import { useT } from "../i18n.js";

export default function Login({ onLogin }) {
  const t = useT();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (!username || !password) {
      setErr(t("login.need"));
      return;
    }
    setBusy(true);
    try {
      const r = await api.login(username, password);
      setAuth(r.token, r.user);
      onLogin(r.user);
    } catch (ex) {
      setErr(ex.message || "login failed");
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
            <div className="brand-title">{t("app.name")}</div>
            <div className="brand-sub">{t("app.sub")}</div>
          </div>
        </div>
        <label className="login-field">
          <span>{t("login.user")}</span>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus placeholder="admin" />
        </label>
        <label className="login-field">
          <span>{t("login.pass")}</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </label>
        {err && <div className="login-error">{err}</div>}
        <button type="submit" disabled={busy} style={{ width: "100%", marginTop: 4 }}>
          {busy ? t("login.doing") : t("login.title")}
        </button>
        <div className="login-hint">
          {t("login.hint")}
          <br />{t("login.hint2")}
        </div>
      </form>
    </div>
  );
}
