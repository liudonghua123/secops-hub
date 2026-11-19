import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";

export default function AgentChat() {
  const { agentId } = useParams();
  const [agent, setAgent] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef(null);

  const loadSessions = (selectFirst = true) =>
    api.sessions(agentId).then((d) => {
      setSessions(d);
      if (selectFirst && d.length && !activeId) openSession(d[0].id);
    });

  useEffect(() => {
    api.agents().then((list) => setAgent(list.find((a) => String(a.id) === String(agentId))));
    loadSessions();
  }, [agentId]);

  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [messages]);

  const openSession = async (id) => {
    setActiveId(id);
    setMessages(await api.sessionMessages(id));
  };
  const newSession = async () => {
    const r = await api.createSession(agentId);
    await loadSessions(false);
    openSession(r.id);
  };
  const delSession = async (id) => {
    await api.deleteSession(id);
    if (activeId === id) { setActiveId(null); setMessages([]); }
    loadSessions(false);
  };
  const send = async () => {
    const content = input.trim();
    if (!content || busy || !activeId) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content, meta: {} }]);
    try {
      const r = await api.sessionChat(activeId, content);
      setMessages((m) => [...m, { role: "assistant", content: r.answer, meta: r.meta }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: "请求失败：" + e.message, meta: { mode: "error" } }]);
    }
    setBusy(false);
    loadSessions(false);
  };

  const modeTag = (meta = {}) => {
    if (meta.mode === "agentscope")
      return <span className="tag tag-low">{meta.model || "agentscope"} · 工具 {meta.tools?.length || 0}{meta.mcp_errors?.length ? ` · MCP 提示 ${meta.mcp_errors.length}` : ""}</span>;
    if (meta.mode === "rule-engine") return <span className="tag tag-mid">规则引擎降级</span>;
    if (meta.mode === "error") return <span className="tag tag-crit">执行异常</span>;
    return null;
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">{agent ? agent.name : "..."} · 会话</h1>
          <div className="page-desc">{agent?.description}　绑定：MCP {agent?.mcp.length || 0} · Skills {agent?.skills.length || 0} · 知识库 {agent?.kbs.length || 0}</div>
        </div>
        <button onClick={newSession}>新建会话</button>
      </div>

      <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
        <div className="card" style={{ width: 220, flex: "none", maxHeight: "70vh", overflowY: "auto" }}>
          {sessions.map((s) => (
            <div key={s.id} style={{
              padding: "9px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 2,
              background: s.id === activeId ? "var(--accent-weak)" : "transparent",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }} onClick={() => openSession(s.id)}>
              <span style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</span>
              <button className="sm danger" onClick={(e) => { e.stopPropagation(); delSession(s.id); }}>×</button>
            </div>
          ))}
          {sessions.length === 0 && <div className="page-desc">暂无会话，点击「新建会话」开始</div>}
        </div>

        <div className="card chat-box" style={{ flex: 1, height: "70vh" }}>
          <div className="chat-log" ref={logRef}>
            {messages.map((m, i) => (
              <div key={i} className={`bubble ${m.role}`}>
                {m.content}
                {m.role === "assistant" && (
                  <div style={{ marginTop: 6 }}>{modeTag(m.meta)}
                    {m.meta?.mcp_errors?.map((e, j) => <div key={j} className="page-desc" style={{ marginTop: 4 }}>{e}</div>)}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="bubble bot">思考中（可调用工具）...</div>}
            {!activeId && <div className="page-desc">选择或新建一个会话开始对话</div>}
          </div>
          <div className="chat-input">
            <input placeholder="输入问题，回车发送" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} />
            <button onClick={send} disabled={busy || !activeId}>发送</button>
          </div>
        </div>
      </div>
    </>
  );
}
