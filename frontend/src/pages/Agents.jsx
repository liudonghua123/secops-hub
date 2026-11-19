import { useEffect, useState } from "react";
import { api } from "../api.js";

const EMPTY = { name: "", description: "", sys_prompt: "你是单位网络安全值守助手，可查询资产、漏洞、情报，并检索应急预案。回答简洁专业。", model_name: "", mcp_ids: [], skill_ids: [], kb_ids: [], max_iters: 10 };

export default function Agents() {
  const [items, setItems] = useState([]);
  const [opts, setOpts] = useState(null);
  const [editing, setEditing] = useState(null); // null | {id?} & form
  const [form, setForm] = useState(EMPTY);

  const load = () => { api.agents().then(setItems); api.agentOptions().then(setOpts); };
  useEffect(load, []);

  const openNew = () => { setForm(EMPTY); setEditing({}); };
  const openEdit = (a) => { setForm({ ...a }); setEditing({ id: a.id }); };
  const toggle = (key, id) => {
    const ids = form[key].includes(id) ? form[key].filter((x) => x !== id) : [...form[key], id];
    setForm({ ...form, [key]: ids });
  };
  const save = async () => {
    if (!form.name) return alert("名称必填");
    if (editing.id) await api.updateAgent(editing.id, form);
    else await api.createAgent(form);
    setEditing(null); load();
  };
  const del = async (id) => {
    if (!confirm("删除该智能体？（会话不受影响但将无法继续对话）")) return;
    await api.deleteAgent(id); load();
  };

  const bindSection = (key, list, label, render) => (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {list.map((o) => (
          <button key={o.id} className={`sm ${form[key].includes(o.id) ? "" : "ghost"}`} onClick={() => toggle(key, o.id)}>
            {render(o)}
          </button>
        ))}
        {list.length === 0 && <span className="page-desc">暂无可选项，请先在对应管理页创建</span>}
      </div>
    </div>
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">智能体</h1>
          <div className="page-desc">基于 AgentScope 创建不同职责的智能体，配置 MCP / Skills / 知识库，各自独立会话</div>
        </div>
        <button onClick={openNew}>新建智能体</button>
      </div>

      {editing && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} style={{ width: 180 }} />
            <input placeholder="职责描述" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={{ width: 260 }} />
            <input placeholder="模型名（留空用全局）" value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} style={{ width: 180 }} />
            <label style={{ fontSize: 12, color: "var(--ink-soft)", display: "flex", alignItems: "center", gap: 4 }}>
              max_iters <input type="number" value={form.max_iters} onChange={(e) => setForm({ ...form, max_iters: +e.target.value })} style={{ width: 60 }} />
            </label>
          </div>
          <textarea placeholder="系统提示词" value={form.sys_prompt} onChange={(e) => setForm({ ...form, sys_prompt: e.target.value })} style={{ width: "100%", minHeight: 60, marginBottom: 10 }} />
          {opts && (
            <>
              {bindSection("mcp_ids", opts.mcp, "MCP 服务器", (o) => `${o.name}(${o.transport}${o.status === "正常" ? "·已连通" : ""})`)}
              {bindSection("skill_ids", opts.skills, "Skills 技能包", (o) => `${o.name} v${o.version}(${o.source})`)}
              {bindSection("kb_ids", opts.kbs, "知识库", (o) => o.name)}
              {opts.llm.configured
                ? <div className="page-desc" style={{ marginBottom: 8 }}>LLM 已配置，可真跑对话</div>
                : <div className="page-desc" style={{ marginBottom: 8, color: "var(--mid)" }}>未配置 LLM（对话将降级为规则引擎）。设置 LLM_API_BASE / LLM_API_KEY / LLM_MODEL 后重启后端</div>}
              <div style={{ textAlign: "right" }}>
                <button className="ghost" onClick={() => setEditing(null)}>取消</button> <button onClick={save}>保存</button>
              </div>
            </>
          )}
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
        {items.map((a) => (
          <div className="card" key={a.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700, fontSize: 15 }}>{a.name}</div>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="sm ghost" onClick={() => openEdit(a)}>编辑</button>
                <button className="sm danger" onClick={() => del(a.id)}>删除</button>
              </div>
            </div>
            <div className="page-desc" style={{ margin: "6px 0 10px" }}>{a.description || "无描述"}</div>
            <div style={{ fontSize: 12, lineHeight: 1.9 }}>
              <div>MCP：{a.mcp.map((m) => m.name).join("、") || "未绑定"}</div>
              <div>Skills：{a.skills.map((s) => s.name).join("、") || "未绑定"}</div>
              <div>知识库：{a.kbs.map((k) => k.name).join("、") || "未绑定"}</div>
              <div className="page-desc">会话数：{a.session_count} · max_iters {a.max_iters}{a.model_name ? ` · 模型 ${a.model_name}` : ""}</div>
            </div>
            <div style={{ marginTop: 10 }}>
              <a href={`#/agent-chat/${a.id}`}><button className="sm">进入会话</button></a>
            </div>
          </div>
        ))}
        {items.length === 0 && !editing && (
          <div className="card page-desc">还没有智能体。点击右上角「新建智能体」，绑定 MCP / Skills / 知识库后即可开始会话。</div>
        )}
      </div>
    </>
  );
}
