import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useT } from "../i18n.js";

const CODE_PLACEHOLDER = `def tool_my_tool(x: str) -> str:
    """Tool description; the model reads this to decide usage.

    Args:
        x (str): what the parameter means.
    """
    return f"result: {x}"`;

function CodeModal({ skill, onClose, onSaved }) {
  const t = useT();
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.skillCode(skill.id).then((d) => setCode(d.code || ""))
      .catch((e) => setMsg(e.message));
  }, [skill.id]);

  const save = async () => {
    setBusy(true); setMsg("");
    try {
      await api.saveSkillCode(skill.id, code);
      setMsg(t("sk.saved"));
      onSaved();
    } catch (e) { setMsg(e.message); }
    setBusy(false);
  };

  return (
    <>
      <div className="drawer-mask" onClick={onClose} />
      <div className="drawer" style={{ width: 640 }}>
        <h2>{skill.name} · {t("sk.codeTitle")}</h2>
        <div className="page-desc" style={{ marginBottom: 8 }}>{skill.file_path || `skills/${skill.name}.py`}</div>
        <textarea className="code" value={code} onChange={(e) => setCode(e.target.value)}
                  placeholder={CODE_PLACEHOLDER}
                  style={{ width: "100%", minHeight: 320 }} spellCheck={false} />
        {msg && <div className="page-desc" style={{ marginTop: 8 }}>{msg}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 12 }}>
          <button className="ghost" onClick={onClose}>{t("c.cancel")}</button>
          <button onClick={save} disabled={busy}>{busy ? "..." : t("c.save")}</button>
        </div>
      </div>
    </>
  );
}

export default function Skills() {
  const t = useT();
  const [items, setItems] = useState([]);
  const [hub, setHub] = useState(null);
  const [showHub, setShowHub] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [msg, setMsg] = useState("");
  const [upload, setUpload] = useState({ name: "", version: "1.0.0", description: "", code: "" });
  const [editing, setEditing] = useState(null);   // skill row for view/edit modal

  const load = () => { api.skills().then(setItems); api.hubIndex().then(setHub); };
  useEffect(load, []);

  const install = async (s) => {
    setMsg(`${s.name} ${t("sk.installing")}`);
    const r = await api.hubInstall(s.name, s.url);
    setMsg(r.ok ? `${s.name} ${r.action === "updated" ? t("sk.updated") : t("sk.installed")}（v${r.version}）` : `${t("sk.failed")}${r.error}`);
    load();
  };
  const doUpload = async () => {
    if (!upload.name || !upload.code) return alert(t("sk.nameCodeRequired"));
    try {
      const r = await api.uploadSkill(upload);
      setMsg(`${upload.name} ${r.action === "updated" ? t("sk.updated") : t("sk.installed")} · ${r.file_path}`);
      setShowUpload(false); load();
    } catch (e) { setMsg(t("sk.uploadFail") + e.message); }
  };

  const srcTag = (s) => s.source === "builtin" ? <span className="tag tag-info">{t("sk.builtin")}</span>
    : s.source === "hub" ? <span className="tag tag-low">Hub</span> : <span className="tag tag-mid">{t("sk.custom")}</span>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">{t("sk.title")}</h1>
          <div className="page-desc">{t("sk.desc")}</div>
        </div>
        <div>
          <button className="ghost" onClick={() => setShowHub(!showHub)} style={{ marginRight: 8 }}>{t("sk.hub")}</button>
          <button onClick={() => setShowUpload(!showUpload)}>{t("sk.upload")}</button>
        </div>
      </div>

      {msg && <div className="card page-desc" style={{ marginBottom: 12 }}>{msg}</div>}

      {showHub && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h3>{t("sk.hub")}（{hub?.hub === "builtin-demo" ? t("sk.hubDemo") : hub?.hub}）</h3>
          {(hub?.skills || []).map((s) => {
            const installed = items.find((x) => x.name === s.name);
            return (
              <div className="list-item" key={s.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <div>
                  <div className="li-title">{s.name} <span className="tag tag-dim">v{s.version}</span></div>
                  <div className="page-desc">{s.description}</div>
                </div>
                <button className="sm" onClick={() => install(s)}>{installed ? `${t("sk.updateBtn")}（${t("sk.alreadyV")} v${installed.version}）` : t("sk.installBtn")}</button>
              </div>
            );
          })}
        </div>
      )}

      {showUpload && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder={t("sk.name")} value={upload.name} onChange={(e) => setUpload({ ...upload, name: e.target.value })} style={{ width: 160 }} />
            <input placeholder={t("sk.version")} value={upload.version} onChange={(e) => setUpload({ ...upload, version: e.target.value })} style={{ width: 90 }} />
            <input placeholder={t("kb.descLabel")} value={upload.description} onChange={(e) => setUpload({ ...upload, description: e.target.value })} style={{ width: 260 }} />
          </div>
          <textarea className="code" placeholder={CODE_PLACEHOLDER} value={upload.code} onChange={(e) => setUpload({ ...upload, code: e.target.value })} style={{ width: "100%", minHeight: 150 }} spellCheck={false} />
          <div style={{ textAlign: "right", marginTop: 8 }}><button onClick={doUpload}>{t("sk.submit")}</button></div>
        </div>
      )}

      {editing && (
        <CodeModal skill={editing} onClose={() => setEditing(null)} onSaved={load} />
      )}

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr>
              <th>{t("sk.col.skill")}</th><th>{t("sk.col.version")}</th><th>{t("sk.col.source")}</th>
              <th>{t("sk.col.desc")}</th><th>{t("sk.col.status")}</th><th>{t("sk.col.actions")}</th>
            </tr></thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td className="mono">v{s.version}</td>
                  <td>{srcTag(s)}</td>
                  <td className="page-desc" style={{ maxWidth: 380 }}>{s.description}</td>
                  <td><span className={`tag ${s.enabled ? "tag-low" : "tag-dim"}`}>{s.enabled ? t("sk.enabled") : t("sk.disabled")}</span></td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    {s.source !== "builtin" && (
                      <>
                        <button className="sm ghost" onClick={() => setEditing(s)}>{t("c.view")}/{t("c.edit")}</button>
                        {" "}<button className="sm ghost" onClick={async () => { await api.toggleSkill(s.id); load(); }}>{s.enabled ? t("sk.disabled") : t("sk.enabled")}</button>
                        {" "}<button className="sm danger" onClick={async () => { if (confirm(t("sk.delConfirm"))) { await api.deleteSkill(s.id); load(); } }}>{t("c.delete")}</button>
                      </>
                    )}
                    {s.source === "builtin" && <span className="page-desc">{t("sk.builtinNote")}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
