import { useEffect, useState } from "react";
import { api } from "../api.js";

const sevTag = (s) => `tag tag-${s === "严重" ? "crit" : s === "高危" ? "high" : s === "中危" ? "mid" : "low"}`;

export default function Scans() {
  const [tasks, setTasks] = useState([]);
  const [engines, setEngines] = useState([]);
  const [findings, setFindings] = useState(null);
  const [activeTask, setActiveTask] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", target_scope: "", engine: "nuclei" });
  const [nuclei, setNuclei] = useState(null);

  const load = () => api.tasks().then(setTasks);
  useEffect(() => { load(); api.engines().then(setEngines); api.nucleiStatus().then(setNuclei); }, []);

  const openFindings = async (t) => {
    setActiveTask(t);
    setFindings(await api.findings(t.id));
  };
  const create = async () => {
    if (!form.name || !form.target_scope) return alert("任务名称与目标范围必填");
    await api.createTask(form);
    setShowAdd(false);
    load();
  };
  const start = async (id) => {
    await api.startTask(id);
    load();
  };
  const review = async (fid, action) => {
    await api.reviewFinding(fid, action);
    setFindings(await api.findings(activeTask.id));
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">扫描任务</h1>
          <div className="page-desc">POC 扫描编排与结果人工复核（确认 / 误报）——仅限授权资产范围</div>
        </div>
        {nuclei && (
          <span className={`tag ${nuclei.available ? "tag-low" : "tag-dim"}`} title={nuclei.note || nuclei.path}>
            {nuclei.available ? `Nuclei 就绪 ${nuclei.version || ""}` : "Nuclei 未安装（回退模拟引擎）"}
          </span>
        )}
        <button onClick={() => setShowAdd(!showAdd)}>{showAdd ? "收起" : "新建任务"}</button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder="任务名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: 220 }} />
            <input placeholder="目标范围（逗号分隔的资产/IP）" value={form.target_scope} onChange={(e) => setForm({ ...form, target_scope: e.target.value })} style={{ width: 300 }} />
            <select value={form.engine} onChange={(e) => setForm({ ...form, engine: e.target.value })}>
              {engines.map((e) => <option key={e.key} value={e.key}>{e.name}</option>)}
            </select>
            <button onClick={create}>创建</button>
          </div>
        </div>
      )}

      <div className="card">
        <table>
          <thead><tr><th>任务名称</th><th>目标范围</th><th>引擎</th><th>状态</th><th>进度</th><th>操作</th></tr></thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td style={{ fontWeight: 600 }}>{t.name}</td>
                <td className="mono" style={{ color: "var(--ink-soft)" }}>{t.target_scope}</td>
                <td>{engines.find((e) => e.key === t.engine)?.name || t.engine}</td>
                <td>
                  <span className={`tag ${t.status === "已完成" ? "tag-low" : t.status === "执行中" ? "tag-info" : "tag-dim"}`}>{t.status}</span>
                </td>
                <td style={{ minWidth: 120 }}>
                  <div className="progress-bar"><div style={{ width: `${t.progress}%` }} /></div>
                </td>
                <td>
                  {t.status !== "已完成" && <button className="sm" onClick={() => start(t.id)}>执行</button>}
                  {" "}
                  <button className="sm ghost" onClick={() => openFindings(t)}>发现</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {findings && (
        <>
          <div className="drawer-mask" onClick={() => setFindings(null)} />
          <div className="drawer">
            <h2>{activeTask.name} · 扫描发现</h2>
            <div className="page-desc">带 PoC 的结果才值得报告（借鉴 Shannon 验证闭环）；每条发现需人工复核</div>
            {findings.map((f) => (
              <div className="list-item" key={f.id}>
                <div className="li-title">{f.vuln_title}</div>
                <div className="li-meta">
                  <span className={sevTag(f.severity)}>{f.severity}</span>
                  <span className="mono">{f.asset_value}</span>
                  <span className="mono">{f.poc_ref}</span>
                  {f.verified && <span className="tag tag-low">已确认</span>}
                  {f.false_positive && <span className="tag tag-dim">已标记误报</span>}
                  {!f.verified && !f.false_positive && <span className="tag tag-high">待复核</span>}
                </div>
                <div style={{ fontSize: 12.5, color: "var(--ink-soft)", marginTop: 6 }}>证据：{f.evidence}</div>
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <button className="sm" onClick={() => review(f.id, "confirm")}>确认漏洞</button>
                  <button className="sm danger" onClick={() => review(f.id, "false_positive")}>标记误报</button>
                </div>
              </div>
            ))}
            {findings.length === 0 && <p className="page-desc">暂无发现</p>}
            <div style={{ marginTop: 14, textAlign: "right" }}>
              <button className="ghost" onClick={() => setFindings(null)}>关闭</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
