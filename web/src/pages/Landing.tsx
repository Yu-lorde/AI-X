import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { HeroFlow } from "../components/HeroFlow";
import { CloverIcon, ArrowIcon, MoonIcon, SparkIcon, SunIcon } from "../components/Icons";
import { useTheme } from "../theme";
import type { WorkSummary } from "../types";
import { formatTime } from "../utils";

const SCENES = [
  {
    img: "/media/campus.jpg",
    tag: "高校学生",
    title: "开学季",
    body: "课程学习、宿舍使用、日常携带，按读者关心的问题组织产品信息。",
  },
  {
    img: "/media/office-desk.jpg",
    tag: "职场办公",
    title: "职场办公",
    body: "文档处理、会议协作、移动办公，说明设备用途与适用条件。",
  },
  {
    img: "/media/creator.jpg",
    tag: "内容创作",
    title: "内容创作",
    body: "图文、设计、视频等创作任务，梳理对应的产品能力与限制。",
  },
];

const STEPS = [
  {
    no: "01",
    title: "填写创作要求",
    body: "产品型号、目标读者、业务场景、发布平台，四项信息确定文案方向。",
  },
  {
    no: "02",
    title: "生成并核验",
    body: "检索知识库成稿，逐项核验产品事实与合规用语，引用来源与待确认信息单独列出。",
  },
  {
    no: "03",
    title: "编辑与保存版本",
    body: "左侧编辑文字与配图，右侧实时预览。确认后保存为新版本，可随时回看或继续编辑。",
  },
];

const DOCS = ["MateBook D 14 产品介绍.pdf", "大学生笔记本电脑选购指南", "开学季数码产品使用场景分析"];

export function LandingPage() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const [historyStatus, setHistoryStatus] = useState<"loading" | "ready" | "error">("loading");
  const [recent, setRecent] = useState<WorkSummary[]>([]);

  useEffect(() => {
    api
      .works()
      .then((data) => {
        if (data.error) throw new Error(data.error);
        setRecent((data.works || []).slice(0, 3));
        setHistoryStatus("ready");
      })
      .catch(() => { setRecent([]); setHistoryStatus("error"); });
  }, []);

  const jump = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="landing">
      <section className="hero-shell">
        <HeroFlow />
        <header className="landing-head">
          <Link className="landing-brand" to="/" title="回到首页">
            <span className="brand-mark"><CloverIcon />
            </span>
            <span>
              <strong>懂你所需</strong>
              <small>营销内容工作台</small>
            </span>
          </Link>
          <div className="landing-head-actions">
            <button type="button" className="landing-link" onClick={() => jump("scenes")}>
              使用场景
            </button>
            <button type="button" className="landing-link" onClick={() => navigate("/history")}>
              历史作品
            </button>
            <button type="button" className="icon-btn on-dark" onClick={toggle} title="切换日间 / 夜间">
              {theme === "light" ? <MoonIcon size={16} /> : <SunIcon size={16} />}
            </button>
          </div>
        </header>

        <div className="hero-inner">
          <div className="hero-copy">
            <p className="hero-eyebrow reveal">华为终端 · 营销内容智能体</p>
            <h1 className="reveal">
              从一条需求到一篇软文，
              <br />
              讲好全场景产品故事
            </h1>
            <p className="hero-sub reveal">
              先检索产品知识库，再按平台模板成稿。
              <br />
              产品参数、配图型号、合规用语逐项核验，每个产品事实都有出处。
            </p>
            <p className="hero-detail reveal">保存编辑版本，可随时回溯。<br />以终端产品为核心，按多设备协同的使用场景组织卖点，不同产品之间的表述保持一致。</p>
            <div className="hero-actions reveal">
              <button type="button" className="btn primary xl hero-cta" onClick={() => navigate("/workspace")}>
                <SparkIcon size={17} />
                开始创作
                <ArrowIcon size={15} />
              </button>
              <button type="button" className="hero-link" onClick={() => navigate("/history")}>
                看看生成过的文稿
                <ArrowIcon size={14} />
              </button>
            </div>
            <ul className="hero-metrics reveal" aria-label="支持范围与版本管理">
              <li><strong>8</strong><span>业务场景</span></li>
              <li><strong>13</strong><span>发布平台</span></li>
              <li className="metric-version"><span>每次保存一个版本</span><small>改动可回溯</small></li>
            </ul>
          </div>
        </div>
      </section>

      <section className="landing-example" id="example">
        <h2 className="example-section-title">成稿示例</h2>
        <div className="example-copy">
          <p className="sec-eyebrow">开学季文案示例</p>
          <h2>从创作要求到文案初稿</h2>
          <p>填写产品、读者、场景和平台后，查看生成内容、参考资料与待确认信息。</p>
          <button type="button" className="example-link" onClick={() => navigate("/workspace")}>
            使用此示例
            <ArrowIcon size={14} />
          </button>
        </div>

        <aside className="hero-card">
          <div className="hero-card-top">
            <span className="chip subtle">小红书</span>
            <span className="chip">开学季</span>
            <span className="hero-tag">示例内容</span>
          </div>
          <h2>大一新生选笔记本先看什么？</h2>
          <p className="hero-card-lead">机身 1.39kg，14 英寸屏幕，日常背包不占地方。课程软件与办公配置以对应型号产品资料为准。</p>
          <p className="example-disclosure">以上参数与核验数量仅用于界面演示，不代表本次检索或核验结果。</p>
          <div className="hero-card-actions">
            <span className="card-action">
              <SparkIcon size={13} />
              编辑文案
            </span>
            <span className="card-action">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                <path d="M6 3.5h8l4 4v13H6z" />
                <path d="M14 3.5v4h4" />
              </svg>
              查看资料
            </span>
            <span className="card-action">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                <path d="M5 4h13v16H5z" />
                <path d="M8 4v4h7" />
              </svg>
              保存版本
            </span>
          </div>
          <div className="hero-card-foot">
            <span className="pill ok">
              <i className="dot" />
              事实核验 5 项通过（示例）
            </span>
            <span className="pill warn">
              <i className="dot" />
              1 项待确认（示例）
            </span>
          </div>
        </aside>
      </section>

      <section className="landing-scenes" id="scenes">
        <div className="scenes-head">
          <h2>已适配的业务场景</h2>
          <p>同一套产品知识库，按读者与发布平台切换写法和配图。</p>
        </div>
        <div className="scene-grid">
          {SCENES.map((scene) => (
            <button
              key={scene.title}
              type="button"
              className="scene-card"
              onClick={() => navigate("/workspace")}
            >
              <span className="scene-media">
                <img src={scene.img} alt="" loading="lazy" />
                <em>{scene.tag}</em>
              </span>
              <span className="scene-body">
                <strong>{scene.title}</strong>
                <small>{scene.body}</small>
              </span>
            </button>
          ))}
        </div>
      </section>

      <section className="landing-steps">
        <div className="scenes-head">
          <h2>创作流程</h2>
          <p>从需求到成稿，每一步都有据可查。</p>
        </div>
        <div className="step-grid">
          {STEPS.map((step, index) => (
            <article key={step.no} className="step-card">
              <span className="step-no">{step.no}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>

              {index === 0 ? (
                <div className="step-preview">
                  <span className="preview-row">
                    <span>产品型号</span>
                    <b>MateBook D 14</b>
                  </span>
                  <span className="preview-row">
                    <span>目标读者</span>
                    <b>大学新生</b>
                  </span>
                  <span className="preview-row">
                    <span>发布平台</span>
                    <b>小红书</b>
                  </span>
                </div>
              ) : null}

              {index === 1 ? (
                <div className="step-preview">
                  <span className="preview-title">参考资料（示例）</span>
                  {DOCS.map((doc) => (
                    <span key={doc} className="preview-doc">
                      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                        <path d="M6 3.5h8l4 4v13H6z" />
                        <path d="M14 3.5v4h4" />
                      </svg>
                      {doc}
                    </span>
                  ))}
                </div>
              ) : null}

              {index === 2 ? (
                <div className="step-preview">
                  <span className="preview-ver">
                    <b className="ver-badge">V2</b>
                    开学季学生购机文案
                    <span className="ver-now">当前版本 · 示例</span>
                  </span>
                  <span className="preview-ver">
                    <b className="ver-badge muted">V1</b>
                    初稿：大学生电脑选购指南
                  </span>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className="landing-recent">
          <div className="recent-head">
            <h2>最近作品</h2>
            <button type="button" className="btn ghost small" onClick={() => navigate("/history")}>
              全部历史
            </button>
          </div>
          {recent.length === 0 && <div className="recent-empty">
            <strong>{historyStatus === "loading" ? "正在读取历史作品…" : historyStatus === "error" ? "暂时无法读取历史作品" : "暂无历史作品"}</strong>
            <p>{historyStatus === "error" ? "请稍后重试，或前往全部历史查看。" : "保存第一篇文案后，可在这里继续编辑或查看版本。"}</p>
          </div>}
          <div className="recent-list">
            {recent.map((item) => (
              <button
                key={item.work_id}
                type="button"
                className="recent-row"
                onClick={() => navigate(`/workspace/${item.work_id}`)}
              >
                <span className="recent-main">
                  <strong>{item.title || "未命名"}</strong>
                  <small>
                    {item.platform || "未标平台"} · {item.version_count} 个版本 · {formatTime(item.updated_at)}
                  </small>
                </span>
                <span className="recent-go">
                  继续编辑
                  <ArrowIcon size={14} />
                </span>
              </button>
            ))}
          </div>
        </section>

      <footer className="landing-foot">
        <strong>懂你所需</strong>
        <span>面向华为产品的营销内容智能体</span>
        <span>知识库检索、事实核验、合规检查与版本管理。</span>
        <span className="credit">场景配图来自 Unsplash，遵循 Unsplash License，可商用、免署名。</span>
      </footer>
    </div>
  );
}
