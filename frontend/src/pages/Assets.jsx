import { useEffect, useState } from "react";
import { api } from "../api.js";

const TYPE_LABEL = { domain: "域名", ip: "主机/IP", app: "应用", host: "主机" };

export default function Assets() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [criticality, setCriticality] = useState("");
  const [profile, setProfile] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const [form, setForm] = useState({ name: "", type: "domain", value: "", owner_dept: "", criticality: "中", icp_no: "", exposure: false, fingerprint: "" });
  const PAGE_SIZE = 20;

  const load = () => {
    const p = new URLSearchParams({ page, page_size: PAGE_SIZE });
    if (q) p.set("q", q);
    if (type) p.set("type", type);
    if (criticality) p.set("criticality", criticality);
    api.assets(`?${p}`).then((d) => {
      setItems(d.items);
      setTotal(d.total);
    });
  };
  useEffect(load, [q, type, criticality, page]);

  const openProfile = async (id) => setProfile(await api.assetProfile(id));
  const add = async () => {
    if (!form.name || !form.value) return alert("名称与值必填");
    await api.createAsset(form);
    setShowAdd(false);
    load();
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">资产管理</h1>
          <div className="page-desc">单位资产台账：域名 / IP / 应用，备案与暴露面，指纹与风险画像</div>
        </div>
        <button onClick={() => setShowAdd(!showAdd)}>{showAdd ? "收起" : "新增资产"}</button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder="资产名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <input placeholder="值（域名/IP/名称）" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} style={{ width: 220 }} />
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              {Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input placeholder="责任部门" value={form.owner_dept} onChange={(e) => setForm({ ...form, owner_dept: e.target.value })} />
            <select value={form.criticality} onChange={(e) => setForm({ ...form, criticality: e.target.value })}>
              <option>高</option><option>中</option><option>低</option>
            </select>
            <input placeholder="备案号（选填）" value={form.icp_no} onChange={(e) => setForm({ ...form, icp_no: e.target.value })} />
            <input placeholder="指纹，逗号分隔" value={form.fingerprint} onChange={(e) => setForm({ ...form, fingerprint: e.target.value })} style={{ width: 200 }} />
            <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
              <input type="checkbox" checked={form.exposure} onChange={(e) => setForm({ ...form, exposure: e.target.checked })} /> 互联网暴露
            </label>
            <button onClick={add}>保存</button>
          </div>
        </div>
      )}

      <div className="toolbar">
        <input placeholder="搜索名称 / 值 / 部门" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 240 }} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">全部类型</option>
          {Object.entries(TYPE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={criticality} onChange={(e) => { setPage(1); setCriticality(e.target.value); }}>
          <option value="">全部关键性</option>
          <option>高</option><option>中</option><option>低</option>
        </select>
        <span className="page-desc" style={{ alignSelf: "center" }}>共 {total} 项</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <label className="ghost sm" style={{ display: "inline-flex", alignItems: "center", cursor: "pointer", border: "1px solid var(--line)", borderRadius: 10, padding: "3px 10px", fontSize: 12, color: "var(--ink-soft)" }}>
            批量导入
            <input type="file" accept=".xlsx,.csv" style={{ display: "none" }}
              onChange={async (e) => {
                const f = e.target.files[0];
                if (!f) return;
                setImportMsg("导入中…");
                try {
                  const r = await api.importAssets(f);
                  setImportMsg(`新增 ${r.added}，更新 ${r.updated}，跳过 ${r.skipped}${r.errors.length ? `，错误 ${r.errors.length}` : ""}`);
                  load();
                } catch (ex) {
                  setImportMsg(`导入失败：${ex.message}`);
                }
                e.target.value = "";
              }} />
          </label>
          <button className="ghost sm" onClick={() => api.exportAssets("xlsx")}>导出 Excel</button>
          <button className="ghost sm" onClick={() => api.exportAssets("csv")}>导出 CSV</button>
        </div>
      </div>
      {importMsg && <div className="card page-desc" style={{ marginBottom: 12 }}>{importMsg}</div>}

      <div className="card">
        <table>
          <thead>
            <tr><th>名称</th><th>值</th><th>类型</th><th>部门</th><th>关键性</th><th>暴露面</th><th>指纹</th><th>操作</th></tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <td style={{ fontWeight: 600 }}>{a.name}</td>
                <td className="mono">{a.value}</td>
                <td>{TYPE_LABEL[a.type] || a.type}</td>
                <td>{a.owner_dept}</td>
                <td><span className={`tag tag-${a.criticality === "高" ? "crit" : a.criticality === "中" ? "mid" : "low"}`}>{a.criticality}</span></td>
                <td>{a.exposure ? <span className="tag tag-high">暴露</span> : <span className="tag tag-dim">内网</span>}</td>
                <td className="mono" style={{ color: "var(--ink-soft)" }}>{a.fingerprint}</td>
                <td><button className="sm ghost" onClick={() => openProfile(a.id)}>画像</button></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan="8" className="page-desc" style={{ textAlign: "center", padding: 24 }}>没有匹配的资产，可点击右上角「批量导入」从 Excel/CSV 导入</td></tr>}
          </tbody>
        </table>
      </div>

      {(() => {
        const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
        if (pages <= 1) return null;
        return (
          <div className="pager">
            <button className="sm ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
            <span className="page-desc">第 {page} / {pages} 页</span>
            <button className="sm ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>下一页</button>
          </div>
        );
      })()}

      {profile && (
        <>
          <div className="drawer-mask" onClick={() => setProfile(null)} />
          <div className="drawer">
            <h2>{profile.asset.name} · 资产画像</h2>
            <div className="page-desc">多维度资产信息聚合（借鉴 ARL-Next 资产画像）</div>
            <dl className="kv">
              <dt>类型 / 值</dt><dd>{TYPE_LABEL[profile.asset.type]} · <span className="mono">{profile.asset.value}</span></dd>
              <dt>责任部门</dt><dd>{profile.asset.owner_dept}</dd>
              <dt>关键性</dt><dd>{profile.asset.criticality}</dd>
              <dt>互联网暴露</dt><dd>{profile.asset.exposure ? "是" : "否"}</dd>
              <dt>备案号</dt><dd>{profile.asset.icp_no || "无"}</dd>
              <dt>技术指纹</dt><dd>{profile.fingerprint_list.join("、") || "无"}</dd>
              <dt>风险评分</dt><dd style={{ fontWeight: 700, color: profile.risk_score >= 15 ? "var(--crit)" : profile.risk_score >= 7 ? "var(--high)" : "var(--ok)" }}>{profile.risk_score}</dd>
            </dl>
            <h3 style={{ margin: "14px 0 8px" }}>匹配漏洞（{profile.matched_vulns.length}）</h3>
            <table>
              <thead><tr><th>漏洞</th><th>级别</th><th>POC</th><th>状态</th></tr></thead>
              <tbody>
                {profile.matched_vulns.map((v) => (
                  <tr key={v.id}>
                    <td>{v.title}</td>
                    <td><span className={`tag tag-${v.severity === "严重" ? "crit" : v.severity === "高危" ? "high" : v.severity === "中危" ? "mid" : "low"}`}>{v.severity}</span></td>
                    <td>{v.poc_available ? "有" : "无"}</td>
                    <td>{v.status}</td>
                  </tr>
                ))}
                {profile.matched_vulns.length === 0 && <tr><td colSpan="4" className="page-desc">未匹配到已知漏洞</td></tr>}
              </tbody>
            </table>
            <div style={{ marginTop: 14, textAlign: "right" }}>
              <button className="ghost" onClick={() => setProfile(null)}>关闭</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
