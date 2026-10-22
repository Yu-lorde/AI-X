import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { ArrowIcon, HistoryIcon, PlusIcon, TrashIcon } from "../components/Icons";
import type { WorkSummary } from "../types";
import { formatTime } from "../utils";

export function HistoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<WorkSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.works();
      setItems(data.works || []);
      if (data.error) setError(`历史存储暂不可用：${data.error}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "读取历史失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const remove = async (item: WorkSummary) => {
    if (!window.confirm(`确定删除《${item.title || "未命名"}》？所有版本都会删除，且无法恢复。`)) return;
    try {
      await api.remove(item.work_id);
      setItems((current) => current.filter((work) => work.work_id !== item.work_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  };

  return (
    <div className="page scroll-page">
      <header className="page-head">
        <div>
          <h1>历史作品</h1>
          <p className="page-sub">
            只显示当前浏览器生成的作品，共 {items.length} 篇。每篇作品保存一次修改就多一个版本。
          </p>
        </div>
        <div className="head-actions">
          <button type="button" className="btn primary" onClick={() => navigate("/")}>
            <PlusIcon size={15} />
            新建创作
          </button>
        </div>
      </header>

      {error ? <div className="banner error"><p>{error}</p></div> : null}

      {loading ? (
        <div className="history-grid">
          {[0, 1, 2].map((index) => (
            <div className="card history-card skeleton-card" key={index}>
              <span className="skeleton-line short" />
              <span className="skeleton-line" />
              <span className="skeleton-line" />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon"><HistoryIcon size={30} /></div>
          <h2>还没有历史作品</h2>
          <p>生成一篇完整文案后，会自动保存为 V1，并出现在这里。</p>
          <div className="empty-actions">
            <button type="button" className="btn primary" onClick={() => navigate("/")}>
              去写第一篇
            </button>
          </div>
        </div>
      ) : (
        <div className="history-grid">
          {items.map((item) => (
            <article key={item.work_id} className="card history-card" onClick={() => navigate(`/workspace/${item.work_id}`)}>
              <div className="card-top">
                <span className="chip subtle">{item.platform || "未标平台"}</span>
                <span className="version-badge">V{item.latest_no || 1}</span>
              </div>
              <h3>{item.title || "未命名"}</h3>
              <p className="history-sub">
                {item.version_count} 个版本 · 更新于 {formatTime(item.updated_at)}
              </p>
              <div className="card-actions">
                <span className="open-link">
                  打开继续编辑
                  <ArrowIcon size={14} />
                </span>
                <button
                  type="button"
                  className="icon-btn danger"
                  title="删除作品"
                  onClick={(event) => {
                    event.stopPropagation();
                    void remove(item);
                  }}
                >
                  <TrashIcon size={15} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <p className="foot-note">历史数据保存在本机 SQLite，清理浏览器 Cookie 后无法再找回对应作品。</p>
    </div>
  );
}
