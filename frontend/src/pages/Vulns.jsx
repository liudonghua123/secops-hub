import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";

const sevTag = (s) => `tag tag-${s === "严重" ? "crit" : s === "高危" ? "high" : s === "中危" ? "mid" : "low"}`;
const PAGE_SIZE = 20;

export default function Vulns() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [detail, setDetail] = useState(null);
  const [brief, setBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [err, setErr] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();

  const load = () => {
    const p = new URLSearchParams({ page, page_size: PAGE_SIZE });
    if (q) p.set("q", q);
    if (severity) p.set("severity", severity);
    if (status) p.set("status", status);
    api.vulns(`?${p}`).then((d) => {
      setItems(d.items);
      setTotal(d.total);
    }).catch((e) => setErr(e.message));
  };
  useEffect(load, [q, severity, status, page]);
  useEffect(() => { setSelected(new Set()); }, [page, q, severity, status]);

  // 预警中心跳转打开详情
  const jumpId = searchParams.get("v");
  useEffect(() => {
    if (jumpId) {
      openDetail(Number(jumpId));
      setSearchParams({}, { replace: true });
    }
  }, [jumpId]);

  const openDetail = async (id) => {
    setBrief(null);
    setErr("");
    try {
      setDetail(await api.vuln(id));
    } catch (e) {
      setErr(e.message);
    }
  };
  const genBrief = async (id) => {
    setBriefLoading(true);
    try {
      setBrief(await api.vulnBrief(id));
    } catch (e) {
      setErr(e.message);
    }
    setBriefLoading(false);
  };
  const changeStatus = async (id, st, note) => {
    try {
      await api.setVulnStatus(id, st, note);
      setDetail(await api.vuln(id));
      load();
    } catch (e) {
      setErr(e.message);
    }
  };
  const genReport = async (ids) => {
    setErr("");
    try {
      await api.vulnDocxPost(ids);
    } catch (e) {
      setErr(e.message);
    }
  };
  const toggleSel = (id) => {
    const s = new Set(selected);
    if (s.has(id)) s.delete(id); else s.add(id);
    setSelected(s);
  };
  const selAll = () => {
    setSelected(selected.size === items.length ? new Set() : new Set(items.map((v) => v.id)));
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const canWrite = ["admin", "analyst"].includes(getStoredRole());

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">漏洞库</h1>
          <div className="page-desc">CVE / CNVD / CNNVD 漏洞归一管理，与资产指纹联动预警，支持处置流转与通报导出</div>
        </div>
      </div>

      <div className="toolbar">
        <input placeholder="搜索编号或关键词" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} style={{ width: 260 }} />
        <select value={severity} onChange={(e) => { setPage(1); setSeverity(e.target.value); }}>
          <option value="">全部级别</option>
          <option>严重</option><option>高危</option><option>中危</option><option>低危</option>
        </select>
        <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          <option value="">全部状态</option>
          <option>未处置</option><option>处置中</option><option>已修复</option><option>已忽略</option>
        </select>
        <span className="page-desc" style={{ alignSelf: "center" }}>共 {total} 条</span>
        {canWrite && selected.size > 0 && (
          <button onClick={() => genReport([...selected])} style={{ marginLeft: "auto" }}>
            生成通报（已选 {selected.size} 项）
          </button>
        )}
      </div>

      {err && <div className="card" style={{ marginBottom: 12, borderColor: "rgba(248,81,73,.4)", color: "var(--crit)" }}>{err}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              {canWrite && <th style={{ width: 32 }}><input type="checkbox" checked={items.length > 0 && selected.size === items.length} onChange={selAll} /></th>}
              <th>漏洞名称</th><th>编号</th><th>级别</th><th>CVSS</th><th>POC</th><th>在野利用</th><th>影响资产</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            {items.map((v) => (
              <tr key={v.id} style={{ cursor: "pointer" }} onClick={() => openDetail(v.id)}>
                {canWrite && (
                  <td onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" checked={selected.has(v.id)} onChange={() => toggleSel(v.id)} />
                  </td>
                )}
                <td style={{ fontWeight: 600 }}>{v.title}</td>
                <td className="mono">{v.cve_id || v.cnvd_id || v.cnnvd_id}</td>
                <td><span className={sevTag(v.severity)}>{v.severity}</span></td>
                <td className="mono">{v.cvss}</td>
                <td>{v.poc_available ? <span className="tag tag-crit">有</span> : <span className="tag tag-dim">无</span>}</td>
                <td>{v.exploited_in_wild ? <span className="tag tag-crit">是</span> : <span className="tag tag-dim">否</span>}</td>
                <td>
                  {v.matched_assets.length > 0
                    ? <span className="tag tag-high">{v.matched_assets.length} 项</span>
                    : <span className="tag tag-dim">0</span>}
                </td>
                <td><span className={`tag ${v.status === "已修复" ? "tag-low" : v.status === "处置中" ? "tag-info" : v.status === "已忽略" ? "tag-dim" : "tag-high"}`}>{v.status}</span></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={canWrite ? 9 : 8} className="page-desc" style={{ textAlign: "center", padding: 24 }}>没有匹配的漏洞记录</td></tr>}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="pager">
          <button className="sm ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
          <span className="page-desc">第 {page} / {pages} 页</span>
          <button className="sm ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>下一页</button>
        </div>
      )}

      {detail && (
        <>
          <div className="drawer-mask" onClick={() => setDetail(null)} />
          <div className="drawer">
            <h2>{detail.title}</h2>
            <div className="page-desc">
              {(detail.cve_id && `CVE: ${detail.cve_id}  `)}
              {(detail.cnvd_id && `CNVD: ${detail.cnvd_id}  `)}
              {(detail.cnnvd_id && `CNNVD: ${detail.cnnvd_id}`)}
            </div>
            <dl className="kv">
              <dt>级别 / CVSS</dt><dd><span className={sevTag(detail.severity)}>{detail.severity}</span>　<span className="mono">{detail.cvss}</span></dd>
              <dt>来源</dt><dd>{detail.source}</dd>
              <dt>披露时间</dt><dd>{detail.published_at}</dd>
              <dt>POC / 在野</dt><dd>{detail.poc_available ? "POC 已公开" : "POC 未见公开"} / {detail.exploited_in_wild ? "已在野利用" : "未见在野利用"}</dd>
              <dt>处置状态</dt><dd><span className="tag tag-info">{detail.status}</span></dd>
            </dl>
            {canWrite && (
              <div className="card" style={{ background: "var(--panel-2)", marginBottom: 12 }}>
                <h3>处置操作</h3>
                <div className="toolbar" style={{ marginBottom: 6 }}>
                  {["处置中", "已修复", "已忽略", "未处置"].map((st) => (
                    <button key={st} className={st === "已修复" ? "" : "ghost sm"} style={st === "已修复" ? {} : {}}
                      onClick={() => {
                        const note = st === "已忽略" ? (prompt("忽略原因（可选）") || "") : "";
                        changeStatus(detail.id, st, note);
                      }}>
                      {detail.status === st ? `✓ ${st}` : st}
                    </button>
                  ))}
                </div>
                <button className="ghost sm" onClick={() => genReport([detail.id])}>导出 Word 处置通报</button>
              </div>
            )}
            <h3 style={{ margin: "12px 0 6px" }}>漏洞描述</h3>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: "var(--ink)" }}>{detail.description}</p>
            <h3 style={{ margin: "12px 0 6px" }}>修复建议</h3>
            <p style={{ fontSize: 13, lineHeight: 1.7 }}>{detail.fix_suggestion || "待补充"}</p>
            <h3 style={{ margin: "12px 0 6px" }}>受影响资产（{detail.matched_assets.length}）</h3>
            {detail.matched_assets.map((a) => (
              <div className="list-item" key={a.id}>
                <div className="li-title">{a.name} <span className="mono" style={{ color: "var(--ink-soft)" }}>{a.value}</span></div>
                <div className="li-meta"><span>{a.owner_dept}</span><span>关键性 {a.criticality}</span></div>
              </div>
            ))}
            {detail.matched_assets.length === 0 && <p className="page-desc">未匹配到本单位资产</p>}
            {detail.events?.length > 0 && (
              <>
                <h3 style={{ margin: "12px 0 6px" }}>处置记录</h3>
                {detail.events.map((e) => (
                  <div className="list-item" key={e.id}>
                    <div className="li-title">{e.action} <span className="page-desc">{e.operator}</span></div>
                    <div className="li-meta">{e.detail} · {e.created_at.slice(0, 19).replace("T", " ")}</div>
                  </div>
                ))}
              </>
            )}
            <h3 style={{ margin: "12px 0 6px" }}>AI 研判简报</h3>
            <button onClick={() => genBrief(detail.id)} disabled={briefLoading}>
              {briefLoading ? "生成中..." : "生成研判简报"}
            </button>
            {brief && (
              <div className="card" style={{ marginTop: 10, background: "var(--panel-2)", whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.8 }}>
                {brief.brief}
                <div style={{ marginTop: 8 }}><span className="badge-mode">生成模式：{brief.mode === "llm" ? "LLM" : "规则引擎兜底"}</span></div>
              </div>
            )}
            <div style={{ marginTop: 14, textAlign: "right" }}>
              <button className="ghost" onClick={() => setDetail(null)}>关闭</button>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function getStoredRole() {
  try {
    return JSON.parse(localStorage.getItem("secops_user") || "null")?.role || "viewer";
  } catch {
    return "viewer";
  }
}
