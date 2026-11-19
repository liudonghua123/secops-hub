import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Intel() {
  const [items, setItems] = useState([]);
  const [sources, setSources] = useState([]);
  const [source, setSource] = useState("");
  const [q, setQ] = useState("");
  const [related, setRelated] = useState(null);
  const [syncStates, setSyncStates] = useState([]);
  const [syncing, setSyncing] = useState("");
  const [syncMsg, setSyncMsg] = useState("");
  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState("");
  const [importSource, setImportSource] = useState("CNVD");

  const load = () => {
    const p = new URLSearchParams();
    if (source) p.set("source", source);
    if (q) p.set("q", q);
    api.intel(`?${p}`).then(setItems);
  };
  useEffect(() => { api.intelSources().then(setSources); api.syncStatus().then(setSyncStates); }, []);
  useEffect(load, [source, q]);

  const openRelated = async (id) => setRelated(await api.relatedVulns(id));

  const doSync = async (key) => {
    setSyncing(key);
    setSyncMsg("");
    try {
      const r = key === "nvd" ? await api.syncNvd() : await api.syncCircl();
      setSyncMsg(r.ok
        ? `${r.source} 同步完成：新增 ${r.add || 0}，更新 ${r.update || 0}，未变化 ${r.same || 0}${r.intel_created ? `，生成情报 ${r.intel_created} 条` : ""}`
        : `同步失败：${r.error}`);
      api.syncStatus().then(setSyncStates);
      load();
    } catch (e) {
      setSyncMsg("同步异常：" + e.message);
    }
    setSyncing("");
  };

  const doImport = async () => {
    setSyncing("import");
    setSyncMsg("");
    try {
      let records;
      try { records = JSON.parse(importText); } catch { return setSyncing(""), setSyncMsg("JSON 解析失败，请检查格式"); }
      const r = await api.syncImport(records.records || records, importSource);
      setSyncMsg(r.ok
        ? `${importSource} 导入完成：收到 ${r.received}，新增 ${r.add}，更新 ${r.update}，跳过 ${r.skip}`
        : `导入失败：${r.error}`);
      api.syncStatus().then(setSyncStates);
      load();
      setShowImport(false);
    } catch (e) {
      setSyncMsg("导入异常：" + e.message);
    }
    setSyncing("");
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">威胁情报</h1>
          <div className="page-desc">聚合 CNNVD / CNVD / NVD / 360CERT / 奇安信 / 绿盟 / OSCS 等多源情报（借鉴 threat-broadcast）</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="toolbar" style={{ marginBottom: 8 }}>
          <h3 style={{ margin: 0 }}>数据源同步</h3>
          <button onClick={() => doSync("nvd")} disabled={!!syncing}>{syncing === "nvd" ? "NVD 同步中..." : "同步 NVD（实时）"}</button>
          <button className="ghost" onClick={() => doSync("circl")} disabled={!!syncing}>{syncing === "circl" ? "CIRCL 同步中..." : "同步 CIRCL（备用）"}</button>
          <button className="ghost" onClick={() => setShowImport(!showImport)}>CNVD/CNNVD 导入</button>
          {syncMsg && <span className="page-desc" style={{ alignSelf: "center" }}>{syncMsg}</span>}
        </div>
        {showImport && (
          <div style={{ marginTop: 8 }}>
            <textarea
              placeholder={'粘贴 CNVD/CNNVD 导出的 JSON（列表或 {"records": [...]}）。字段支持：cve_id/cnvd_id/cnnvd_id、title、severity、cvss、description、affected_keywords、fix_suggestion、published_at'}
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              style={{ width: "100%", minHeight: 110, fontFamily: "var(--mono)", fontSize: 12 }}
            />
            <div className="toolbar" style={{ marginTop: 8 }}>
              <select value={importSource} onChange={(e) => setImportSource(e.target.value)}>
                <option>CNVD</option><option>CNNVD</option>
              </select>
              <button onClick={doImport} disabled={!!syncing}>{syncing === "import" ? "导入中..." : "执行导入"}</button>
            </div>
          </div>
        )}
        <div style={{ fontSize: 12, color: "var(--ink-soft)", lineHeight: 1.8 }}>
          {syncStates.map((s) => (
            <div key={s.key}>
              <span style={{ color: s.mode === "api" ? "var(--ok)" : "var(--mid)" }}>{s.mode === "api" ? "[实时]" : "[导入]"}</span>
              {" "}{s.name}：{s.note}{s.last_sync ? `　上次同步 ${s.last_sync.at.replace("T", " ")}` : "　从未同步"}
            </div>
          ))}
        </div>
      </div>

      <div className="toolbar">
        {sources.map((s) => (
          <button key={s.source} className={source === s.source ? "" : "ghost"} onClick={() => setSource(source === s.source ? "" : s.source)}>
            {s.source} ({s.count})
          </button>
        ))}
        <input placeholder="搜索情报关键词 / 编号" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginLeft: "auto", width: 240 }} />
      </div>

      <div className="grid grid-2">
        <div className="card">
          {items.map((i) => (
            <div className="list-item" key={i.id}>
              <div className="li-title">{i.title}</div>
              <div className="li-meta">
                <span className="tag tag-info">{i.source}</span>
                {i.severity && <span className={`tag tag-${i.severity === "严重" ? "crit" : i.severity === "高危" ? "high" : i.severity === "中危" ? "mid" : "low"}`}>{i.severity}</span>}
                {i.ref_id && <span className="mono">{i.ref_id}</span>}
                <span>{i.published_at}</span>
                <button className="sm ghost" onClick={() => openRelated(i.id)}>关联漏洞</button>
              </div>
              <div style={{ fontSize: 12.5, color: "var(--ink-soft)", marginTop: 6, lineHeight: 1.6 }}>{i.summary}</div>
            </div>
          ))}
        </div>
        <div className="card" style={{ alignSelf: "start", position: "sticky", top: 0 }}>
          <h3>情报关联漏洞</h3>
          {!related && <p className="page-desc">点击左侧「关联漏洞」查看本地漏洞库匹配结果，并跳转资产影响分析。</p>}
          {related && (
            <>
              <div className="list-item">
                <div className="li-title">{related.intel.title}</div>
                <div className="li-meta"><span className="tag tag-info">{related.intel.source}</span><span>{related.intel.published_at}</span></div>
              </div>
              <h3 style={{ margin: "12px 0 8px" }}>本地漏洞库匹配（{related.vulns.length}）</h3>
              <table>
                <thead><tr><th>漏洞</th><th>级别</th><th>编号</th></tr></thead>
                <tbody>
                  {related.vulns.map((v) => (
                    <tr key={v.id}>
                      <td>{v.title}</td>
                      <td><span className={`tag tag-${v.severity === "严重" ? "crit" : "high"}`}>{v.severity}</span></td>
                      <td className="mono">{v.cve_id || v.cnvd_id}</td>
                    </tr>
                  ))}
                  {related.vulns.length === 0 && (
                    <tr><td colSpan="3" className="page-desc">本地漏洞库暂无该编号，可从情报源手动收录。</td></tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </>
  );
}
