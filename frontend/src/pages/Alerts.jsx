import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Alerts() {
  const [items, setItems] = useState([]);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.alerts(onlyUnread).then((d) => setItems(d.items)).finally(() => setLoading(false));
  };
  useEffect(load, [onlyUnread]);

  const tag = (lv) => (lv === "严重" ? "crit" : lv === "高危" ? "high" : "mid");

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">预警中心</h1>
          <div className="page-desc">高危/严重漏洞入库自动预警；处置完成（已修复/已忽略）后对应预警自动关闭</div>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button className={onlyUnread ? "" : "ghost"} onClick={() => setOnlyUnread(false)}>全部</button>
          <button className={onlyUnread ? "ghost" : ""} onClick={() => setOnlyUnread(true)}>仅未读</button>
          <button className="ghost" onClick={() => api.markAlerts([], true).then(load)}>全部已读</button>
        </div>
      </div>
      {loading && <div className="card page-desc">加载中…</div>}
      {!loading && items.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>✓</div>
          <div className="page-desc">没有预警记录。同步 NVD 或导入高危漏洞后将自动生成。</div>
        </div>
      )}
      <div className="card">
        {items.map((a) => (
          <div key={a.id} className="list-item" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <span className={`tag tag-${tag(a.level)}`} style={{ marginTop: 2 }}>{a.level}</span>
            <div style={{ flex: 1 }}>
              <div className="li-title">{a.title} {!a.read && <span className="tag tag-info">未读</span>}</div>
              <div className="li-meta">{a.detail} · {a.created_at.slice(0, 19).replace("T", " ")}</div>
            </div>
            {!a.read && <button className="sm ghost" onClick={() => api.markAlerts([a.id]).then(load)}>标记已读</button>}
          </div>
        ))}
      </div>
    </>
  );
}
