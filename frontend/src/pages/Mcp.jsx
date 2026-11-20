import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useT } from "../i18n.js";

const EMPTY = { name: "", transport: "http", command: "", args: "", url: "", headers: "{}", enabled: true, note: "" };

export default function Mcp() {
  const t = useT();
  const [items, setItems] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [testMsg, setTestMsg] = useState({});
  const [testing, setTesting] = useState(null);

  const load = () => { api.mcpServers().then(setItems); };
  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!form.name) return alert(t("mcp.name") + "?");
    let args = [];
    try { args = JSON.parse(form.args || "[]"); } catch { alert("args → JSON []"); return; }
    let headers = {};
    try { headers = JSON.parse(form.headers || "{}"); } catch { alert("headers → JSON {}"); return; }
    await api.createMcp({ ...form, args, headers });
    setShowAdd(false); setForm(EMPTY); load();
  };
  const test = async (id) => {
    setTesting(id); setTestMsg((m) => ({ ...m, [id]: t("mcp.testing") }));
    const r = await api.testMcp(id);
    setTestMsg((m) => ({ ...m, [id]: r.ok ? `${t("mcp.ok")}，${r.tools.length}${t("mcp.tools")}${r.tools.join("、")}` : `${t("mcp.fail")}${r.error}` }));
    setTesting(null); load();
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">{t("mcp.title")}</h1>
          <div className="page-desc">{t("mcp.desc")}</div>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}>{showAdd ? t("c.collapse") : t("mcp.register")}</button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder={t("mcp.name")} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: 160 }} />
            <select value={form.transport} onChange={(e) => setForm({ ...form, transport: e.target.value })}>
              <option value="http">streamable-http</option>
              <option value="stdio">stdio</option>
            </select>
            {form.transport === "http"
              ? <input placeholder="URL，如 http://host:port/mcp/" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} style={{ width: 300 }} />
              : <input placeholder="命令，如 npx 或 python" value={form.command} onChange={(e) => setForm({ ...form, command: e.target.value })} style={{ width: 200 }} />}
            {form.transport === "stdio" && <input placeholder='参数 JSON 数组，如 ["-y","server"]' value={form.args} onChange={(e) => setForm({ ...form, args: e.target.value })} style={{ width: 240 }} />}
            <input placeholder='headers JSON，如 {"Authorization":"Bearer x"}' value={form.headers} onChange={(e) => setForm({ ...form, headers: e.target.value })} style={{ width: 240 }} />
            <input placeholder={t("mcp.note")} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} style={{ width: 160 }} />
            <button onClick={save}>{t("c.save")}</button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr>
              <th>{t("mcp.name")}</th><th>{t("mcp.col.transport")}</th><th>{t("mcp.col.addr")}</th>
              <th>{t("mcp.col.status")}</th><th>{t("mcp.col.tools")}</th><th>{t("mcp.col.note")}</th><th>{t("mcp.col.actions")}</th>
            </tr></thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.id}>
                  <td style={{ fontWeight: 600 }}>{m.name}</td>
                  <td><span className="tag tag-info">{m.transport}</span></td>
                  <td className="mono" style={{ color: "var(--ink-soft)" }}>{m.transport === "http" ? m.url : `${m.command} ${m.args}`}</td>
                  <td>
                    <span className={`tag ${m.status === "正常" ? "tag-low" : m.status === "失败" ? "tag-crit" : "tag-dim"}`}>{m.status}</span>
                    {testMsg[m.id] && testMsg[m.id] !== t("mcp.testing") && <div className="page-desc" style={{ marginTop: 4, maxWidth: 320 }}>{testMsg[m.id]}</div>}
                  </td>
                  <td className="mono">{m.tool_count}</td>
                  <td className="page-desc">{m.note}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="sm" onClick={() => test(m.id)} disabled={testing === m.id}>{testing === m.id ? "..." : t("mcp.test")}</button>
                    {" "}<button className="sm danger" onClick={async () => { if (confirm(t("mcp.delConfirm"))) { await api.deleteMcp(m.id); load(); } }}>{t("c.delete")}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {items.length === 0 && <div className="page-desc">{t("mcp.none")}</div>}
      </div>
    </>
  );
}
