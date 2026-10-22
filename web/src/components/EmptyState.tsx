import type { Inputs } from "../types";

const EXAMPLES: { label: string; inputs: Inputs }[] = [
  {
    label: "开学季 · 微信公众号",
    inputs: { product: "MateBook D 14", audience: "学校教务和信息中心", scene: "开学季", platform: "微信公众号", note: "" },
  },
  {
    label: "开学季 · 小红书",
    inputs: { product: "MateBook D 14", audience: "准备开学的大学新生", scene: "开学季", platform: "小红书", note: "" },
  },
];

export function EmptyState({ onExample }: { onExample: (inputs: Inputs) => void }) {
  return (
    <div className="empty-state">
      <svg className="empty-art" viewBox="0 0 220 160" aria-hidden="true">
        <rect x="38" y="18" width="128" height="118" rx="12" fill="var(--art-paper)" stroke="var(--art-line)" />
        <rect x="58" y="36" width="88" height="10" rx="5" fill="var(--art-head)" />
        <rect x="58" y="56" width="64" height="7" rx="3.5" fill="var(--art-line)" />
        <rect x="58" y="72" width="88" height="6" rx="3" fill="var(--art-line)" />
        <rect x="58" y="86" width="74" height="6" rx="3" fill="var(--art-line)" />
        <rect x="58" y="106" width="48" height="6" rx="3" fill="var(--art-line)" />
        <rect x="136" y="60" width="46" height="42" rx="8" fill="var(--art-accent-soft)" stroke="var(--art-accent)" />
        <path d="M159 70l3.2 8.6 8.6 3.2-8.6 3.2-3.2 8.6-3.2-8.6-8.6-3.2 8.6-3.2z" fill="var(--art-accent)" />
        <circle cx="188" cy="30" r="4" fill="var(--art-accent)" opacity=".45" />
        <circle cx="26" cy="112" r="3" fill="var(--art-accent)" opacity=".3" />
      </svg>
      <h2>填写任务信息，生成第一篇文案</h2>
      <p>选好产品型号、人群、场景和平台后，系统会先查知识库，再按平台模板写成稿并自动核验。</p>
      <div className="empty-actions">
        {EXAMPLES.map((item) => (
          <button key={item.label} type="button" className="btn ghost" onClick={() => onExample(item.inputs)}>
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
