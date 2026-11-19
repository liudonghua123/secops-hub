import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

export default function AIChat() {
  const [mode, setMode] = useState(null);
  const [log, setLog] = useState([
    { role: "bot", text: "我是单位安全值守助手。可以问我：某漏洞影响哪些资产、最新高危预警、扫描结果如何复核等。\n\n当前若未配置 LLM 接口，将以规则引擎模式应答（设置 LLM_API_BASE / LLM_API_KEY / LLM_MODEL 环境变量即可接入任意 OpenAI 兼容接口或本地 Ollama，数据不出网）。" },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef(null);

  useEffect(() => { api.aiStatus().then(setMode); }, []);
  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight); }, [log]);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setLog((l) => [...l, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await api.aiChat(q);
      setLog((l) => [...l, { role: "bot", text: r.answer, mode: r.mode }]);
    } catch (e) {
      setLog((l) => [...l, { role: "bot", text: "服务异常：" + e.message }]);
    }
    setBusy(false);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">AI 值守助手</h1>
          <div className="page-desc">漏洞研判 / 资产影响分析 / 处置建议 · LLM 可插拔 + 规则引擎兜底（借鉴 AiSOC 与 CyberSecurity-Intelligence-Platform）</div>
        </div>
        {mode && <span className="badge-mode">当前模式：{mode.llm_available ? "LLM" : "规则引擎兜底"}</span>}
      </div>

      <div className="card chat-box">
        <div className="chat-log" ref={logRef}>
          {log.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>{m.text}{m.mode && <div style={{ marginTop: 6 }}><span className="badge-mode">{m.mode === "llm" ? "LLM 应答" : "规则引擎应答"}</span></div>}</div>
          ))}
          {busy && <div className="bubble bot">思考中...</div>}
        </div>
        <div className="chat-input">
          <input
            placeholder="输入问题，回车发送"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button onClick={send} disabled={busy}>发送</button>
        </div>
      </div>
    </>
  );
}
