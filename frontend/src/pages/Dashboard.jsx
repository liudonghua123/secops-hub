import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";

const SEV_COLOR = { 严重: "#f85149", 高危: "#f0883e", 中危: "#d29922", 低危: "#3fb950" };

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [trend, setTrend] = useState([]);
  const [topRisks, setTopRisks] = useState([]);
  const [intel, setIntel] = useState([]);

  useEffect(() => {
    api.stats().then(setStats);
    api.trend().then(setTrend);
    api.topRisks().then(setTopRisks);
    api.intel().then((d) => setIntel(d.slice(0, 6)));
  }, []);

  if (!stats) return <div className="page-desc">加载中...</div>;

  const kpis = [
    { label: "资产总数", value: stats.asset_total, extra: `互联网暴露 ${stats.asset_exposed} 项` },
    { label: "漏洞总量", value: stats.vuln_total, extra: `未处置 ${stats.vuln_unresolved} 项` },
    { label: "威胁情报", value: stats.intel_total, extra: "多源聚合" },
    { label: "扫描任务", value: stats.task_total, extra: `执行中 ${stats.task_running} 项` },
    { label: "扫描发现", value: stats.finding_total, extra: `已确认 ${stats.finding_verified} / 误报 ${stats.finding_fp}` },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">安全态势总览</h1>
          <div className="page-desc">资产、漏洞、情报、验证处置一体化视图</div>
        </div>
      </div>

      <div className="grid grid-kpi">
        {kpis.map((k) => (
          <div className="card kpi" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-extra">{k.extra}</div>
          </div>
        ))}
        <div className="card kpi">
          <div className="kpi-label">严重级别分布</div>
          <div style={{ marginTop: 6 }}>
            {Object.entries(stats.sev_distribution).map(([s, c]) => (
              <div key={s} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
                <span className={`tag tag-${s === "严重" ? "crit" : s === "高危" ? "high" : s === "中危" ? "mid" : "low"}`}>{s}</span>
                <span className="mono">{c}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginTop: 14 }}>
        <div className="card">
          <h3>高危风险 TOP</h3>
          <table>
            <thead><tr><th>漏洞</th><th>级别</th><th>CVSS</th><th>POC</th></tr></thead>
            <tbody>
              {topRisks.map((r) => (
                <tr key={r.id}>
                  <td>{r.title}</td>
                  <td><span className={`tag tag-${r.severity === "严重" ? "crit" : "high"}`}>{r.severity}</span></td>
                  <td className="mono">{r.cvss}</td>
                  <td>{r.poc_available ? <span className="tag tag-crit">已有</span> : <span className="tag tag-dim">无</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>最新威胁情报</h3>
          {intel.map((i) => (
            <div className="list-item" key={i.id}>
              <div className="li-title">{i.title}</div>
              <div className="li-meta">
                <span className="tag tag-info">{i.source}</span>
                {i.severity && <span className={`tag tag-${i.severity === "严重" ? "crit" : i.severity === "高危" ? "high" : i.severity === "中危" ? "mid" : "low"}`}>{i.severity}</span>}
                <span>{i.published_at}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <h3>漏洞披露趋势（按月）</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a3140" />
            <XAxis dataKey="month" stroke="#8b949e" fontSize={12} />
            <YAxis stroke="#8b949e" fontSize={12} allowDecimals={false} />
            <Tooltip contentStyle={{ background: "#1c2330", border: "1px solid #2a3140", color: "#e6edf3" }} />
            <Bar dataKey="count" name="新增漏洞" radius={[4, 4, 0, 0]}>
              {trend.map((e, i) => <Cell key={i} fill="#4f8ff7" />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
