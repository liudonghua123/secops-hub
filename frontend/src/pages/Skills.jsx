import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Skills() {
  const [items, setItems] = useState([]);
  const [hub, setHub] = useState(null);
  const [showHub, setShowHub] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [msg, setMsg] = useState("");
  const [upload, setUpload] = useState({ name: "", version: "1.0.0", description: "", code: "" });

  const load = () => { api.skills().then(setItems); api.hubIndex().then(setHub); };
  useEffect(load, []);

  const install = async (s) => {
    setMsg(`${s.name} 安装中...`);
    const r = await api.hubInstall(s.name, s.url);
    setMsg(r.ok ? `${s.name} ${r.action === "updated" ? "已更新" : "安装成功"}（v${r.version}）` : `失败：${r.error}`);
    load();
  };
  const doUpload = async () => {
    if (!upload.name || !upload.code) return alert("名称与代码必填");
    try {
      const r = await api.uploadSkill(upload);
      setMsg(`${upload.name} ${r.action === "updated" ? "已更新" : "上传成功"}`);
      setShowUpload(false); load();
    } catch (e) { setMsg("上传失败：" + e.message); }
  };

  const srcTag = (s) => s.source === "builtin" ? <span className="tag tag-info">内置</span>
    : s.source === "hub" ? <span className="tag tag-low">Hub</span> : <span className="tag tag-mid">自定义</span>;

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">Skills 技能管理</h1>
          <div className="page-desc">内置技能 + 自定义上传 + Hub 更新下载；技能包为定义 tool_* 函数的 python 代码</div>
        </div>
        <div>
          <button className="ghost" onClick={() => setShowHub(!showHub)} style={{ marginRight: 8 }}>Hub 市场</button>
          <button onClick={() => setShowUpload(!showUpload)}>上传技能</button>
        </div>
      </div>

      {msg && <div className="card page-desc" style={{ marginBottom: 12 }}>{msg}</div>}

      {showHub && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h3>技能 Hub（{hub?.hub === "builtin-demo" ? "内置演示目录 · 配置 SKILL_HUB_URL 接入远程 Hub" : hub?.hub}）</h3>
          {(hub?.skills || []).map((s) => {
            const installed = items.find((x) => x.name === s.name);
            return (
              <div className="list-item" key={s.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="li-title">{s.name} <span className="tag tag-dim">v{s.version}</span></div>
                  <div className="page-desc">{s.description}</div>
                </div>
                <button className="sm" onClick={() => install(s)}>{installed ? `更新（已装 v${installed.version}）` : "安装"}</button>
              </div>
            );
          })}
        </div>
      )}

      {showUpload && (
        <div className="card" style={{ marginBottom: 14 }}>
          <div className="toolbar">
            <input placeholder="技能名称" value={upload.name} onChange={(e) => setUpload({ ...upload, name: e.target.value })} style={{ width: 160 }} />
            <input placeholder="版本" value={upload.version} onChange={(e) => setUpload({ ...upload, version: e.target.value })} style={{ width: 90 }} />
            <input placeholder="描述" value={upload.description} onChange={(e) => setUpload({ ...upload, description: e.target.value })} style={{ width: 260 }} />
          </div>
          <textarea placeholder={'python 代码，定义 tool_ 开头的函数（带类型注解与 docstring）。例如：\n\ndef tool_my_tool(x: str) -> str:\n    """工具说明，模型据此决定何时调用。\n\n    Args:\n        x (str): 参数说明。\n    """\n    return f"result: {x}"'} value={upload.code} onChange={(e) => setUpload({ ...upload, code: e.target.value })} style={{ width: "100%", minHeight: 150, fontFamily: "var(--mono)", fontSize: 12 }} />
          <div style={{ textAlign: "right", marginTop: 8 }}><button onClick={doUpload}>提交</button></div>
        </div>
      )}

      <div className="card">
        <table>
          <thead><tr><th>技能</th><th>版本</th><th>来源</th><th>说明</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id}>
                <td style={{ fontWeight: 600 }}>{s.name}</td>
                <td className="mono">v{s.version}</td>
                <td>{srcTag(s)}</td>
                <td className="page-desc" style={{ maxWidth: 380 }}>{s.description}</td>
                <td><span className={`tag ${s.enabled ? "tag-low" : "tag-dim"}`}>{s.enabled ? "启用" : "停用"}</span></td>
                <td>
                  {s.source !== "builtin" && (
                    <>
                      <button className="sm ghost" onClick={async () => { await api.toggleSkill(s.id); load(); }}>{s.enabled ? "停用" : "启用"}</button>
                      {" "}<button className="sm danger" onClick={async () => { if (confirm("删除该技能？")) { await api.deleteSkill(s.id); load(); } }}>删除</button>
                    </>
                  )}
                  {s.source === "builtin" && <span className="page-desc">随平台内置</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
