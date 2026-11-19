import { useEffect, useState } from "react";
import { api } from "../api.js";

const EMPTY = { name: "", transport: "http", command: "", args: "", url: "", headers: "{}", enabled: true, note: "" };

export default function Mcp() {
  const [items, setItems] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [testMsg, setTestMsg] = useState({});
  const [testing, setTesting] = useState(null);

  const load = () => api.mcpServers().then(setItems);
  useEffect(load, []);

  const save = async () => {
    if (!form.name) return alert("名称必填");
    let args = [];
    try { args = JSON.parse(form.args || "[]"); } catch { return alert("args 需为 JSON 数组"); }
    let headers = {};
    try { headers = JSON.parse(form.headers || "{}"); } catch { return alert("headers 需为 JSON 对象"); }
    const d = { ...form, args, headers };
    await api.createMcp(d);
    setShowAdd(false); setForm(EMPTY); load();
  };
  const test = async (id) => {
    setTesting(id); setTestMsg((m) => ({ ...m, [id]: "测试中..." }));
    const r = await api.testMcp(id);
    setTestMsg((m) => ({ ...m, [id]: r.ok ? `连通，${r.tools.length} 个工具：${r.tools.join("、")}` : `失败：${r.error}` }));
    setTesting(null); load();
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">MCP 服务器管理</h1>
          <div className="page-desc">内置平台接口（/mcp）+ 第三方 MCP（stdio / streamable-http），供智能体绑定调用</div>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}>{showAdd ? "收起" : "注册服务器"}</button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: 160 }} />
            <select value={form.transport} onChange={(e) => setForm({ ...form, transport: e.target.value })}>
              <option value="http">streamable-http</option>
              <option value="stdio">stdio</option>
            </select>
            {form.transport === "http"
              ? <input placeholder="URL，如 http://host:port/mcp/" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} style={{ width: 300 }} />
              : <input placeholder="命令，如 npx 或 python" value={form.command} onChange={(e) => setForm({ ...form, command: e.target.value })} style={{ width: 200 }} />}
            {form.transport === "stdio" && <input placeholder='参数 JSON 数组，如 ["-y","server"]' value={form.args} onChange={(e) => setForm({ ...form, args: e.target.value })} style={{ width: 240 }} />}
            <input placeholder='headers JSON，如 {"Authorization":"Bearer x"}' value={form.headers} onChange={(e) => setForm({ ...form, headers: e.target.value })} style={{ width: 240 }} />
            <input placeholder="备注" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} style={{ width: 160 }} />
            <button onClick={save}>保存</button>
          </div>
        </div>
      )}

      <div className="card">
        <table>
          <thead><tr><th>名称</th><th>传输</th><th>地址/命令</th><th>状态</th><th>工具数</th><th>备注</th><th>操作</th></tr></thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id}>
                <td style={{ fontWeight: 600 }}>{m.name}</td>
                <td><span className="tag tag-info">{m.transport}</span></td>
                <td className="mono" style={{ color: "var(--ink-soft)" }}>{m.transport === "http" ? m.url : `${m.command} ${m.args}`}</td>
                <td>
                  <span className={`tag ${m.status === "正常" ? "tag-low" : m.status === "失败" ? "tag-crit" : "tag-dim"}`}>{m.status}</span>
                  {testMsg[m.id] && testMsg[m.id] !== "测试中..." && <div className="page-desc" style={{ marginTop: 4, maxWidth: 320 }}>{testMsg[m.id]}</div>}
                </td>
                <td className="mono">{m.tool_count}</td>
                <td className="page-desc">{m.note}</td>
                <td>
                  <button className="sm" onClick={() => test(m.id)} disabled={testing === m.id}>{testing === m.id ? "..." : "连通测试"}</button>
                  {" "}<button className="sm danger" onClick={async () => { if (confirm("删除该 MCP 服务器注册？")) { await api.deleteMcp(m.id); load(); } }}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="page-desc">尚未注册 MCP 服务器。可把平台自身（http://127.0.0.1:8100/mcp/）注册进来供智能体调用。</div>}
      </div>
    </>
  );
}
