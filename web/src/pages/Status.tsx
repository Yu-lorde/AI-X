import { useEffect, useState } from "react";

import { api } from "../api";
import { RefreshIcon } from "../components/Icons";
import type { Meta } from "../types";

export function StatusPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [report, setReport] = useState("");
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .meta()
      .then(setMeta)
      .catch((err) => setError(err instanceof Error ? err.message : "读取状态失败"));
  }, []);

  const test = async () => {
    setTesting(true);
    setReport("");
    try {
      const data = await api.testKb();
      setReport(data.report);
      setMeta((current) => (current ? { ...current, credentials: data.credentials } : current));
    } catch (err) {
      setReport(err instanceof Error ? err.message : "测试失败");
    } finally {
      setTesting(false);
    }
  };

  const credentials = meta?.credentials;
  const llmReady = Boolean(credentials?.llm_key);
  const imaReady = Boolean(credentials?.ima_id && credentials?.ima_key);

  return (
    <div className="page scroll-page">
      <header className="page-head">
        <div>
          <h1>系统状态</h1>
          <p className="page-sub">这里只展示连接状态，不显示任何密钥内容。</p>
        </div>
        <div className="head-actions">
          <button type="button" className="btn ghost" onClick={test} disabled={testing}>
            <RefreshIcon size={15} />
            {testing ? "检测中…" : "测试知识库"}
          </button>
        </div>
      </header>

      {error ? <div className="banner error"><p>{error}</p></div> : null}

      <div className="status-grid">
        <section className="card status-card">
          <div className="status-top">
            <h3>本地知识库</h3>
            <span className={`pill ${meta?.kb.exists ? "ok" : "warn"}`}>
              <i className="dot" />
              {meta?.kb.exists ? "可用" : "未找到"}
            </span>
          </div>
          <p className="status-value">{meta?.source_hint || "读取中…"}</p>
          <code className="path">{meta?.kb.root || "—"}</code>
          <p className="hint">ima 凭证未配置或连接失败时，自动读取这份本地知识库。</p>
        </section>

        <section className="card status-card">
          <div className="status-top">
            <h3>大模型</h3>
            <span className={`pill ${llmReady ? "ok" : "warn"}`}>
              <i className="dot" />
              {llmReady ? "已配置" : "未配置"}
            </span>
          </div>
          <p className="status-value">{llmReady ? "写作接口就绪" : "缺少 LLM_API_KEY"}</p>
          <p className="hint">密钥只从 agent/.env 读取，页面与接口都不会回传密钥内容。</p>
        </section>

        <section className="card status-card">
          <div className="status-top">
            <h3>访客历史</h3>
            <span className="pill neutral">
              <i className="dot" />
              {meta?.history.count ?? 0} 篇作品
            </span>
          </div>
          <p className="status-value">SQLite · 当前浏览器隔离</p>
          <code className="path">{meta?.history.db || "—"}</code>
          <p className="hint">匿名 Cookie 标识访客，不登录、不跨设备同步。</p>
        </section>

        <section className="card status-card">
          <div className="status-top">
            <h3>覆盖范围</h3>
            <span className="pill neutral">
              <i className="dot" />
              P8 / P6 模板
            </span>
          </div>
          <p className="status-value">
            {meta?.scenes.length ?? 0} 个业务场景 · {meta?.platforms.length ?? 0} 个发布平台
          </p>
          <div className="chips wrap">
            {(meta?.platforms || []).slice(0, 6).map((platform) => (
              <span className="chip subtle" key={platform}>
                {platform}
              </span>
            ))}
            {meta && meta.platforms.length > 6 ? <span className="chip subtle">…</span> : null}
          </div>
        </section>
      </div>

      <section className="card status-test">
        <div className="status-top">
          <h3>连接详情</h3>
          <span className="hint">{imaReady ? "ima 凭证已检测到" : "ima 凭证未检测到"}</span>
        </div>
        {report ? <pre className="report">{report}</pre> : <p className="hint">点右上角「测试知识库」查看远程知识库连接结果。</p>}
      </section>

      <p className="foot-note">
        服务地址 127.0.0.1:8000 · 生成逻辑沿用原 agent 流程，未接入新的模型或第三方服务。
      </p>
    </div>
  );
}
