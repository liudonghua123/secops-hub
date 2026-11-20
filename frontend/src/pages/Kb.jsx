import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useT } from "../i18n.js";

const FOLDER_ICON = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>
);
const FILE_ICON = (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6"/></svg>
);
const TWIST = (
  <svg className="twist" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M9 6l6 6-6 6"/></svg>
);

function TreeNode({ node, depth, selectedDoc, onPick, onDeleteFolder, i18n }) {
  const [open, setOpen] = useState(depth < 1);
  if (node.type === "file") {
    const selected = selectedDoc && selectedDoc.id === node.id;
    return (
      <div className={`tree-row ${selected ? "selected" : ""}`} style={{ paddingLeft: 8 }}
           onClick={() => onPick(node)}>
        <span style={{ color: "var(--ink-soft)", display: "grid" }}>{FILE_ICON}</span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.filename || i18n("kb.emptyFolder")}</span>
        <span className="tree-file-meta mono">{(node.size / 1024).toFixed(1)}KB · {node.chunks}{i18n("kb.chunks")}</span>
      </div>
    );
  }
  return (
    <div>
      <div className="tree-row" onClick={() => setOpen(!open)}>
        <span className={`twist ${open ? "open" : ""}`}>{TWIST}</span>
        <span style={{ color: "var(--accent)", display: "grid" }}>{FOLDER_ICON}</span>
        <span style={{ fontWeight: 600 }}>{node.name}</span>
        <span className="tree-file-meta">{node.file_count || 0}</span>
        <button className="sm danger" onClick={(e) => {
          e.stopPropagation();
          if (confirm(i18n("kb.deleteFolder") + "？")) onDeleteFolder(node);
        }}>{i18n("c.delete")}</button>
      </div>
      {open && (
        <div className="tree-children">
          {node.children.map((c, i) => (
            <TreeNode key={c.type === "folder" ? c.name : c.id} node={c} depth={depth + 1}
                      selectedDoc={selectedDoc} onPick={onPick} onDeleteFolder={onDeleteFolder} i18n={i18n} />
          ))}
          {(!node.children || node.children.length === 0) && (
            <div className="page-desc" style={{ padding: "4px 8px" }}>{i18n("kb.noDocs")}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Kb() {
  const t = useT();
  const [kbs, setKbs] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [tree, setTree] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newKb, setNewKb] = useState({ name: "", description: "" });
  const [paste, setPaste] = useState({ filename: "", content: "" });
  const [folder, setFolder] = useState("");      // current target folder
  const [newFolder, setNewFolder] = useState("");
  const [msg, setMsg] = useState("");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState(null);
  const [selDoc, setSelDoc] = useState(null);
  const fileRef = useRef(null);

  const load = () => { api.kbs().then(setKbs); };
  useEffect(() => { load(); }, []);
  const loadTree = (id) => { if (id) api.kbDocs(id).then(setTree); };
  useEffect(() => { loadTree(activeId); }, [activeId]);

  const pickKb = (id) => {
    setActiveId(id);
    setFolder("");
    setSelDoc(null);
    setHits(null);
    setMsg("");
  };

  const createKb = async () => {
    if (!newKb.name) return alert(t("kb.nameRequired"));
    const r = await api.createKb(newKb);
    setShowAdd(false); setNewKb({ name: "", description: "" }); await load();
    pickKb(r.id);
  };
  const addPaste = async () => {
    if (!paste.filename || !paste.content) return alert(t("kb.fileAndContent"));
    const r = await api.addKbDoc(activeId, { ...paste, folder });
    setMsg(`${t("kb.added")}「${folder ? folder + "/" : ""}${paste.filename}」${r.chunks}${t("kb.chunks")}`);
    setPaste({ filename: "", content: "" }); loadTree(activeId); load();
  };
  const uploadFiles = async (files) => {
    if (!files || !files.length) return;
    try {
      const r = await api.uploadKbDocs(activeId, files, folder);
      const ok = r.items.filter((x) => x.ok).length;
      const fail = r.items.filter((x) => !x.ok);
      setMsg(`${t("kb.added")} ${ok}/${r.items.length}` + (fail.length ? ` · ${fail.map((f) => `${f.filename}: ${f.error}`).join("; ")}` : ""));
      loadTree(activeId); load();
    } catch (e) { setMsg(t("kb.uploadFail") + e.message); }
    if (fileRef.current) fileRef.current.value = "";
  };
  const createFolder = async () => {
    if (!newFolder.trim()) return;
    await api.createKbFolder(activeId, newFolder.trim());
    setNewFolder(""); loadTree(activeId); load();
  };
  const deleteFolder = async (node) => {
    const path = findPath(tree, node) || node.name;
    await api.deleteKbFolder(activeId, path);
    setSelDoc(null); loadTree(activeId); load();
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
          <h1 className="page-title">{t("kb.title")}</h1>
          <div className="page-desc">{t("kb.desc")}</div>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}>{showAdd ? t("c.collapse") : t("kb.new")}</button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder={t("kb.name")} value={newKb.name} onChange={(e) => setNewKb({ ...newKb, name: e.target.value })} style={{ width: 200 }} />
            <input placeholder={t("kb.descLabel")} value={newKb.description} onChange={(e) => setNewKb({ ...newKb, description: e.target.value })} style={{ width: 320 }} />
            <button onClick={createKb}>{t("kb.create")}</button>
          </div>
        </div>
      )}

      <div className="kb-layout">
        <div className="card kb-side">
          {kbs.map((k) => (
            <div key={k.id} className={`tree-row ${k.id === activeId ? "selected" : ""}`} onClick={() => pickKb(k.id)}>
              <span style={{ color: "var(--accent)", display: "grid" }}>{FOLDER_ICON}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{k.name}</div>
                <div className="page-desc">{k.doc_count}{t("kb.docs")} · {k.folder_count}{t("kb.folders")}</div>
              </div>
            </div>
          ))}
          {kbs.length === 0 && <div className="page-desc">{t("kb.noKb")}</div>}
        </div>

        <div style={{ flex: 1, minWidth: 0, width: "100%" }}>
          {active && (
            <div className="card" style={{ marginBottom: 14 }}>
              <h3>{active.name} · {t("kb.tree")}{folder ? ` / ${folder}` : ""}</h3>
              <div className="toolbar">
                <input placeholder={t("kb.folderName")} value={newFolder} onChange={(e) => setNewFolder(e.target.value)}
                       onKeyDown={(e) => e.key === "Enter" && createFolder()} style={{ width: 200 }} />
                <button className="ghost" onClick={createFolder}>{t("kb.newFolder")}</button>
                <input ref={fileRef} type="file" multiple
                       accept=".txt,.md,.csv,.json,.log,.py,.yaml,.yml,.html"
                       onChange={(e) => uploadFiles(e.target.files)} />
                <button className="danger" style={{ marginLeft: "auto" }}
                        onClick={async () => { if (confirm(t("kb.delKbConfirm"))) { await api.deleteKb(activeId); setActiveId(null); setTree([]); load(); } }}>
                  {t("kb.delKb")}
                </button>
              </div>
              <div className="toolbar" style={{ marginBottom: 6 }}>
                <span className="page-desc">{t("kb.paste")}{folder ? ` → ${folder}` : ""}</span>
                <input placeholder={t("kb.filename")} value={paste.filename} onChange={(e) => setPaste({ ...paste, filename: e.target.value })} style={{ width: 160 }} />
                <input placeholder={t("kb.test")} value={query} onChange={(e) => setQuery(e.target.value)} style={{ width: 180 }} onKeyDown={(e) => e.key === "Enter" && search()} />
                <button className="ghost" onClick={search}>{t("c.search")}</button>
              </div>
              <textarea placeholder={t("kb.desc")} value={paste.content} onChange={(e) => setPaste({ ...paste, content: e.target.value })} style={{ width: "100%", minHeight: 80, fontFamily: "var(--sans)", fontSize: 12.5 }} />
              <div style={{ textAlign: "right", marginTop: 8 }}><button onClick={addPaste}>{t("kb.pasteIn")}</button></div>
              {msg && <div className="page-desc" style={{ marginTop: 8 }}>{msg}</div>}
            </div>
          )}

          {hits && (
            <div className="card" style={{ marginBottom: 14 }}>
              <h3>{t("kb.results")}（{hits.length}）</h3>
              {hits.map((h, i) => (
                <div className="list-item" key={i}>
                  <div className="li-meta"><span className="tag tag-info">{h.kb_doc || h.doc}</span><span>{h.score}</span></div>
                  <div style={{ fontSize: 12.5, marginTop: 4, lineHeight: 1.7 }}>{h.text}</div>
                </div>
              ))}
              {hits.length === 0 && <div className="page-desc">{t("kb.noHits")}</div>}
            </div>
          )}

          {active && (
            <div className="card">
              <div className="kb-tree">
                {tree.length === 0 && <div className="page-desc">{t("kb.noDocs")}</div>}
                {tree.map((node, i) => (
                  <TreeNode key={node.type === "folder" ? node.name : node.id} node={node} depth={0}
                            selectedDoc={selDoc} onPick={setSelDoc} onDeleteFolder={deleteFolder} i18n={t} />
                ))}
              </div>
            </div>
          )}
          {!active && <div className="card page-desc">{t("kb.pickKb")}</div>}
        </div>
      </div>
    </>
  );
}

// find the full path of a folder node in the tree (parent chain)
function findPath(nodes, target, prefix = "") {
  for (const n of nodes) {
    if (n.type !== "folder") continue;
    const path = prefix ? `${prefix}/${n.name}` : n.name;
    if (n === target) return path;
    const found = findPath(n.children || [], target, path);
    if (found) return found;
  }
  return null;
}
