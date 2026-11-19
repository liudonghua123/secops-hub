import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

export default function Kb() {
  const [kbs, setKbs] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [docs, setDocs] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newKb, setNewKb] = useState({ name: "", description: "" });
  const [paste, setPaste] = useState({ filename: "", content: "" });
  const [msg, setMsg] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState(null);
  const fileRef = useRef(null);

  const load = () => api.kbs().then(setKbs);
  useEffect(load, []);
  useEffect(() => { if (activeId) api.kbDocs(activeId).then(setDocs); }, [activeId]);

  const createKb = async () => {
    if (!newKb.name) return alert("名称必填");
    await api.createKb(newKb);
    setShowAdd(false); setNewKb({ name: "", description: "" }); load();
  };
  const addPaste = async () => {
    if (!paste.filename || !paste.content) return alert("文件名与内容必填");
    const r = await api.addKbDoc(activeId, paste);
    setMsg(`已入库「${paste.filename}」，切分为 ${r.chunks} 个片段`);
    setPaste({ filename: "", content: "" }); api.kbDocs(activeId).then(setDocs);
  };
  const uploadFile = async (f) => {
    if (!f) return;
    try {
      const r = await api.uploadKbDoc(activeId, f);
      setMsg(`已上传「${f.name}」，切分为 ${r.chunks} 个片段`);
      api.kbDocs(activeId).then(setDocs);
    } catch (e) { setMsg("上传失败：" + e.message); }
    fileRef.current.value = "";
  };
  const search = async () => {
    if (!query || !activeId) return;
    setHits(await api.kbSearch(activeId, query));
  };

  const active = kbs.find((k) => k.id === activeId);

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">知识库管理</h1>
          <div className="page-desc">上传制度/预案/设备资料，自动分块供智能体检索（离线关键词检索，无需外部服务）</div>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}>{showAdd ? "收起" : "新建知识库"}</button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder="知识库名称" value={newKb.name} onChange={(e) => setNewKb({ ...newKb, name: e.target.value })} style={{ width: 200 }} />
            <input placeholder="描述" value={newKb.description} onChange={(e) => setNewKb({ ...newKb, description: e.target.value })} style={{ width: 320 }} />
            <button onClick={createKb}>创建</button>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
        <div className="card" style={{ width: 230, flex: "none" }}>
          {kbs.map((k) => (
            <div key={k.id} style={{
              padding: "9px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 2,
              background: k.id === activeId ? "var(--accent-weak)" : "transparent",
            }} onClick={() => setActiveId(k.id)}>
              <div style={{ fontSize: 13.5, fontWeight: 600 }}>{k.name}</div>
              <div className="page-desc">{k.doc_count} 个文档 · {k.description}</div>
            </div>
          ))}
          {kbs.length === 0 && <div className="page-desc">暂无知识库</div>}
        </div>

        <div style={{ flex: 1 }}>
          {active && (
            <div className="card" style={{ marginBottom: 14 }}>
              <div className="toolbar">
                <input ref={fileRef} type="file" accept=".txt,.md,.csv,.json,.log,.py,.yaml,.yml,.html" onChange={(e) => uploadFile(e.target.files[0])} />
                <span className="page-desc">或粘贴文本</span>
                <input placeholder="文件名" value={paste.filename} onChange={(e) => setPaste({ ...paste, filename: e.target.value })} style={{ width: 160 }} />
                <input placeholder="检索测试…" value={query} onChange={(e) => setQuery(e.target.value)} style={{ width: 180 }} onKeyDown={(e) => e.key === "Enter" && search()} />
                <button className="ghost" onClick={search}>检索</button>
                <button className="danger" style={{ marginLeft: "auto" }} onClick={async () => { if (confirm("删除整个知识库及其所有文档？")) { await api.deleteKb(activeId); setActiveId(null); setDocs([]); load(); } }}>删除知识库</button>
              </div>
              <textarea placeholder="粘贴文档内容，空行分段会按语义分块" value={paste.content} onChange={(e) => setPaste({ ...paste, content: e.target.value })} style={{ width: "100%", minHeight: 80, fontFamily: "var(--sans)", fontSize: 12.5 }} />
              <div style={{ textAlign: "right", marginTop: 8 }}><button onClick={addPaste}>入库</button></div>
              {msg && <div className="page-desc" style={{ marginTop: 8 }}>{msg}</div>}
            </div>
          )}

          {hits && (
            <div className="card" style={{ marginBottom: 14 }}>
              <h3>检索结果（{hits.length}）</h3>
              {hits.map((h, i) => (
                <div className="list-item" key={i}>
                  <div className="li-meta"><span className="tag tag-info">{h.doc}</span><span>相关度 {h.score}</span></div>
                  <div style={{ fontSize: 12.5, marginTop: 4, lineHeight: 1.7 }}>{h.text}</div>
                </div>
              ))}
              {hits.length === 0 && <div className="page-desc">无匹配片段</div>}
            </div>
          )}

          {active && (
            <div className="card">
              <h3>{active.name} · 文档列表</h3>
              <table>
                <thead><tr><th>文件名</th><th>大小</th><th>片段数</th><th>入库时间</th><th></th></tr></thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.id}>
                      <td className="mono">{d.filename}</td>
                      <td className="mono">{(d.size / 1024).toFixed(1)} KB</td>
                      <td className="mono">{d.chunks}</td>
                      <td className="page-desc">{d.created_at.slice(0, 19)}</td>
                      <td><button className="sm danger" onClick={async () => { await api.deleteKbDoc(activeId, d.id); api.kbDocs(activeId).then(setDocs); }}>删除</button></td>
                    </tr>
                  ))}
                  {docs.length === 0 && <tr><td colSpan="5" className="page-desc">暂无文档</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          {!active && <div className="card page-desc">左侧选择一个知识库管理文档</div>}
        </div>
      </div>
    </>
  );
}
