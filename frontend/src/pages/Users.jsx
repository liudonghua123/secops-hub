import { useEffect, useState } from "react";
import { api } from "../api.js";

const ROLES = ["admin", "analyst", "viewer"];
const ROLE_LABEL = { admin: "管理员", analyst: "分析员", viewer: "只读" };

export default function Users() {
  const [users, setUsers] = useState([]);
  const [editing, setEditing] = useState(null); // null | {} | user copy
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const load = () => api.users().then(setUsers).catch((e) => setErr(e.message));
  useEffect(load, []);

  const save = async () => {
    setErr(""); setMsg("");
    try {
      if (editing.id) {
        await api.updateUser(editing.id, editing);
        setMsg("已保存");
      } else {
        await api.createUser(editing);
        setMsg("已创建");
      }
      setEditing(null);
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  const del = async (u) => {
    if (!confirm(`确认删除用户「${u.display_name}」？`)) return;
    try {
      await api.deleteUser(u.id);
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">用户与权限</h1>
          <div className="page-desc">管理员可管理账号；分析员可处置与导入；只读仅查看</div>
        </div>
        <button onClick={() => setEditing({ username: "", password: "", display_name: "", role: "viewer", enabled: true })}>新建用户</button>
      </div>
      {msg && <div className="card page-desc" style={{ marginBottom: 12 }}>{msg}</div>}
      {err && <div className="card" style={{ marginBottom: 12, borderColor: "rgba(248,81,73,.4)", color: "var(--crit)" }}>{err}</div>}

      {editing && (
        <div className="card" style={{ marginBottom: 14 }}>
          <h3>{editing.id ? "编辑用户" : "新建用户"}</h3>
          <div className="toolbar">
            <input placeholder="用户名" value={editing.username} onChange={(e) => setEditing({ ...editing, username: e.target.value })} style={{ width: 160 }} />
            <input placeholder={editing.id ? "密码（留空不改）" : "初始密码"} type="password" value={editing.password} onChange={(e) => setEditing({ ...editing, password: e.target.value })} style={{ width: 160 }} />
            <input placeholder="显示名" value={editing.display_name} onChange={(e) => setEditing({ ...editing, display_name: e.target.value })} style={{ width: 140 }} />
            <select value={editing.role} onChange={(e) => setEditing({ ...editing, role: e.target.value })}>
              {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
            </select>
            <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
              <input type="checkbox" checked={editing.enabled} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} /> 启用
            </label>
            <button onClick={save}>保存</button>
            <button className="ghost" onClick={() => setEditing(null)}>取消</button>
          </div>
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr><th>用户名</th><th>显示名</th><th>角色</th><th>状态</th><th></th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={{ fontWeight: 600 }}>{u.username}</td>
                <td>{u.display_name}</td>
                <td><span className="tag tag-info">{ROLE_LABEL[u.role]}</span></td>
                <td>{u.enabled ? <span className="tag tag-low">启用</span> : <span className="tag tag-dim">停用</span>}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button className="sm ghost" onClick={() => setEditing({ ...u, password: "" })}>编辑</button>{" "}
                  <button className="sm danger" onClick={() => del(u)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
