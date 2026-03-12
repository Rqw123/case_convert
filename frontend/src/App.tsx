import { useState } from "react";

type ParseSummary = {
  id: number;
  summary: Record<string, any>;
};

type MatchResponse = {
  task_id: number;
  task_code: string;
  status: string;
  summary: {
    case_count: number;
    matched_case_count: number;
    unmatched_case_count: number;
  };
  results: Array<{
    case_id: string;
    case_step: string;
    matched: boolean;
    case_info: Array<{
      signal_desc?: string | null;
      msg_id?: string | null;
      signal_name: string;
      signal_val?: string | null;
      info_str?: string | null;
      match_reason?: string | null;
    }>;
    unmatched_reason?: string | null;
  }>;
};

async function postFile(url: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(url, { method: "POST", body: formData });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

export default function App() {
  const [signalFile, setSignalFile] = useState<File | null>(null);
  const [caseFile, setCaseFile] = useState<File | null>(null);
  const [signalSummary, setSignalSummary] = useState<ParseSummary | null>(null);
  const [caseSummary, setCaseSummary] = useState<ParseSummary | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResponse | null>(null);
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("deepseek-chat");
  const [temperature, setTemperature] = useState("0");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const parseSignals = async () => {
    if (!signalFile) return;
    setBusy(true);
    setMessage("解析信号文件中...");
    try {
      const data = await postFile("/api/signals/parse", signalFile);
      setSignalSummary(data);
      setMessage("信号文件解析完成");
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  const parseCases = async () => {
    if (!caseFile) return;
    setBusy(true);
    setMessage("解析测试用例中...");
    try {
      const data = await postFile("/api/cases/parse", caseFile);
      setCaseSummary(data);
      setMessage("测试用例解析完成");
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  const runMatch = async () => {
    if (!signalSummary || !caseSummary) return;
    setBusy(true);
    setMessage("调用 DeepSeek 匹配中...");
    try {
      const response = await fetch("/api/match/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          signal_source_id: signalSummary.summary.signal_source_id,
          case_batch_id: caseSummary.summary.case_batch_id,
          llm_config: {
            base_url: baseUrl,
            api_key: apiKey,
            model,
            temperature: Number(temperature),
            timeout_seconds: 60
          }
        })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = await response.json();
      setMatchResult(data);
      setMessage("匹配完成");
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  const exportResult = async () => {
    if (!matchResult || !caseSummary) return;
    setBusy(true);
    setMessage("导出回填文件中...");
    try {
      const params = new URLSearchParams({
        task_id: String(matchResult.task_id),
        case_batch_id: String(caseSummary.summary.case_batch_id)
      });
      const response = await fetch(`/api/export/fill?${params.toString()}`, { method: "POST" });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = await response.json();
      window.open(data.export_url, "_blank");
      setMessage("导出文件已生成");
    } catch (error) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Case Convert v1</p>
        <h1>自然语言测试用例信号匹配工具</h1>
        <p className="sub">
          上传 DBC 或 Excel 信号矩阵，再上传测试用例表，系统会持久化全过程数据，并调用 DeepSeek 输出结构化匹配结果。
        </p>
      </section>

      <section className="grid">
        <div className="card">
          <h2>1. 信号源上传</h2>
          <input type="file" accept=".dbc,.xls,.xlsx,.xlsm" onChange={(event) => setSignalFile(event.target.files?.[0] ?? null)} />
          <button disabled={!signalFile || busy} onClick={parseSignals}>解析信号文件</button>
          {signalSummary && (
            <div className="summary">
              <p>信号源ID: {signalSummary.summary.signal_source_id}</p>
              <p>报文数: {signalSummary.summary.message_count}</p>
              <p>信号数: {signalSummary.summary.signal_count}</p>
            </div>
          )}
        </div>

        <div className="card">
          <h2>2. 测试用例上传</h2>
          <input type="file" accept=".xls,.xlsx,.xlsm" onChange={(event) => setCaseFile(event.target.files?.[0] ?? null)} />
          <button disabled={!caseFile || busy} onClick={parseCases}>解析测试用例</button>
          {caseSummary && (
            <div className="summary">
              <p>用例批次ID: {caseSummary.summary.case_batch_id}</p>
              <p>用例数: {caseSummary.summary.case_count}</p>
            </div>
          )}
        </div>

        <div className="card full">
          <h2>3. 模型配置</h2>
          <div className="form-grid">
            <label>
              Base URL
              <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
            </label>
            <label>
              API Key
              <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
            </label>
            <label>
              Model
              <input value={model} onChange={(event) => setModel(event.target.value)} />
            </label>
            <label>
              Temperature
              <input value={temperature} onChange={(event) => setTemperature(event.target.value)} />
            </label>
          </div>
          <div className="actions">
            <button disabled={!signalSummary || !caseSummary || !apiKey || busy} onClick={runMatch}>执行匹配</button>
            <button disabled={!matchResult || busy} onClick={exportResult}>导出回填结果</button>
          </div>
          <p className="status">{message}</p>
        </div>
      </section>

      {matchResult && (
        <section className="card result">
          <h2>4. 匹配结果</h2>
          <p>任务编号: {matchResult.task_code}</p>
          <p>
            总数 {matchResult.summary.case_count} / 成功 {matchResult.summary.matched_case_count} / 失败 {matchResult.summary.unmatched_case_count}
          </p>
          <div className="result-list">
            {matchResult.results.map((item) => (
              <article key={`${item.case_id}-${item.case_step}`} className="result-item">
                <h3>{item.case_id}</h3>
                <p>{item.case_step}</p>
                <p className={item.matched ? "ok" : "bad"}>{item.matched ? "匹配成功" : "未匹配"}</p>
                {item.case_info.map((info, index) => (
                  <pre key={index}>{JSON.stringify(info, null, 2)}</pre>
                ))}
                {!item.matched && <p>{item.unmatched_reason}</p>}
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
