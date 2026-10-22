import { useMemo, useState, type RefObject } from "react";

import type { Preview, WorkMeta } from "../types";
import { ArticleView } from "./ArticleView";
import { CopyIcon, DownloadIcon } from "./Icons";

const TABS = [
  { key: "preview", label: "成稿预览" },
  { key: "checks", label: "核验" },
  { key: "sources", label: "依据" },
  { key: "export", label: "导出" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function checkClass(line: string): string {
  if (line.startsWith("通过")) return "check-pass";
  if (line.startsWith("待确认")) return "check-warn";
  return "check-risk";
}

export function PreviewPanel({
  preview,
  meta,
  scrollRef,
}: {
  preview: Preview;
  meta: WorkMeta;
  scrollRef?: RefObject<HTMLDivElement | null>;
}) {
  const [tab, setTab] = useState<TabKey>("preview");
  const [copied, setCopied] = useState(false);

  const pending = useMemo(() => {
    const v = preview.verification;
    return [v.facts, v.images, v.compliance, v.pending].flat().filter((line) => line.startsWith("待确认")).length;
  }, [preview.verification]);

  const blocks = [
    { title: "产品事实", items: preview.verification.facts },
    { title: "图片型号", items: preview.verification.images },
    { title: "合规", items: preview.verification.compliance },
    { title: "待确认信息", items: preview.verification.pending },
  ];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(preview.export_text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  const download = () => {
    const blob = new Blob([preview.export_text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${preview.article.title || "文案"}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="preview-shell">
      <div className="preview-toolbar">
        <div className="segmented">
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={tab === item.key ? "active" : ""}
              onClick={() => setTab(item.key)}
            >
              {item.label}
              {item.key === "checks" && pending > 0 ? <em>{pending}</em> : null}
            </button>
          ))}
        </div>
        <div className="preview-actions">
          <button type="button" className="icon-btn" title="复制导出文本" onClick={copy}>
            <CopyIcon size={16} />
          </button>
          <button type="button" className="icon-btn" title="下载 txt" onClick={download}>
            <DownloadIcon size={16} />
          </button>
          {copied ? <span className="copied">已复制</span> : null}
        </div>
      </div>

      <div className="preview-scroll" ref={scrollRef}>
        {tab === "preview" ? (
          <>
            {preview.intro ? <p className="scene-line">{preview.intro}</p> : null}
            <ArticleView article={preview.article} />
          </>
        ) : null}

        {tab === "checks" ? (
          <div className="checks">
            {blocks.map((block) => (
              <section key={block.title} className="check-block">
                <h3>
                  {block.title}
                  <span>{block.items.length}</span>
                </h3>
                {block.items.length ? (
                  <ul>
                    {block.items.map((line, index) => (
                      <li key={index} className={block.title === "待确认信息" ? "check-warn" : checkClass(line)}>
                        {line}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="hint">暂无内容</p>
                )}
              </section>
            ))}
          </div>
        ) : null}

        {tab === "sources" ? (
          <div className="sources">
            <section className="source-block">
              <h3>本次任务</h3>
              <dl className="kv">
                {Object.entries(meta.strategy).map(([key, value]) => (
                  <div key={key}>
                    <dt>{STRATEGY_LABELS[key] || key}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
                {meta.platform_title ? (
                  <div>
                    <dt>平台模板</dt>
                    <dd>{meta.platform_title}</dd>
                  </div>
                ) : null}
                <div>
                  <dt>资料来源</dt>
                  <dd>{meta.source || "—"}</dd>
                </div>
              </dl>
            </section>

            <section className="source-block">
              <h3>事实点</h3>
              {preview.article.facts.length ? (
                <ul className="fact-list">
                  {preview.article.facts.map((fact, index) => (
                    <li key={index}>
                      {fact.point}
                      <span>来源：{fact.source_title}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="hint">本次没有可回链的事实点。</p>
              )}
            </section>

            <section className="source-block">
              <h3>引用的知识库文档</h3>
              {meta.scenario_docs.length || meta.documents.length ? (
                <ul className="doc-list">
                  {meta.scenario_docs.map((doc, index) => (
                    <li key={`s${index}`}>
                      <em>P8/{doc.role}</em>
                      {doc.title}
                    </li>
                  ))}
                  {meta.documents.map((doc, index) => (
                    <li key={`d${index}`}>
                      <em>P1</em>
                      {doc.title}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="hint">暂无文档记录。</p>
              )}
            </section>
          </div>
        ) : null}

        {tab === "export" ? (
          <div className="export-pane">
            <div className="export-head">
              <span>整理好的导出文本，可直接交给运营或存档。</span>
              <div className="export-buttons">
                <button type="button" className="btn ghost small" onClick={copy}>
                  <CopyIcon size={14} />
                  {copied ? "已复制" : "复制全文"}
                </button>
                <button type="button" className="btn ghost small" onClick={download}>
                  <DownloadIcon size={14} />
                  下载 txt
                </button>
              </div>
            </div>
            <pre>{preview.export_text}</pre>
          </div>
        ) : null}
      </div>
    </div>
  );
}

const STRATEGY_LABELS: Record<string, string> = {
  product: "产品型号",
  audience: "目标人群",
  scene: "业务场景",
  platform: "发布平台",
  parent_title: "P8 母文档",
  module_id: "行业模块",
  module_brief: "内容目标",
  template_query: "模板检索词",
};
