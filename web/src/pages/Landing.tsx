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
    title: "开学季 · 宿舍 · 课堂",
    body: "围绕课程学习、宿舍使用和日常携带，介绍相关产品特点。",
  },
  {
    img: "/media/office-desk.jpg",
    tag: "职场办公",
    title: "通勤 · 会议 · 移动办公",
    body: "围绕文档处理、会议和移动办公，介绍设备用途与适用条件。",
  },
  {
    img: "/media/creator.jpg",
    tag: "内容创作",
    title: "图文 · 种草 · 短视频脚本",
    body: "结合图文、设计和视频任务，整理产品介绍重点。",
  },
];

const STEPS = [
  {
    no: "01",
    title: "填写创作要求",
    body: "填写产品、读者、业务场景和发布平台，补充相关重点。",
  },
  {
    no: "02",
    title: "生成并核对内容",
    body: "根据资料生成初稿，查看引用来源和待确认信息。",
  },
  {
    no: "03",
    title: "编辑与保存版本",
    body: "修改文字和配图，保存当前版本或继续编辑历史作品。",
  },
];

const DOCS = ["MateBook D 14 产品介绍.pdf", "大学生笔记本电脑选购指南", "开学季数码产品使用场景分析"];

export function LandingPage() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const [recent, setRecent] = useState<WorkSummary[]>([]);

  useEffect(() => {
    api
      .works()
      .then((data) => setRecent((data.works || []).slice(0, 3)))
      .catch(() => setRecent([]));
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
            <h1 className="reveal">
              基于产品资料
              <br />
              生成营销文案
            </h1>
            <p className="hero-sub reveal">
              结合目标读者与发布平台生成初稿，支持图文编辑、资料核对和版本保存。
            </p>
            <div className="hero-actions reveal">
              <button type="button" className="btn primary xl hero-cta" onClick={() => navigate("/workspace")}>
                <SparkIcon size={17} />
                开始创作
                <ArrowIcon size={15} />
              </button>
              <button type="button" className="hero-link" onClick={() => jump("example")}>
                查看成稿示例
                <ArrowIcon size={14} />
              </button>
            </div>
            <ul className="hero-steps reveal">
              <li>
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                  <path d="M6 3.5h8l4 4v13H6z" />
                  <path d="M14 3.5v4h4" />
                </svg>
                产品资料
              </li>
              <li className="sep" aria-hidden="true">
                <ArrowIcon size={12} />
              </li>
              <li>
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                  <path d="M4 6h16M4 12h11M4 18h7" />
                </svg>
                文案生成
              </li>
              <li className="sep" aria-hidden="true">
                <ArrowIcon size={12} />
              </li>
              <li>
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                  <circle cx="12" cy="12" r="8.5" />
                  <path d="M8.5 12.2l2.4 2.4 4.6-4.8" />
                </svg>
                来源核对
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="landing-example" id="example">
        <div className="example-copy">
          <p className="sec-eyebrow">成稿示例</p>
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
          <h2>大学新生选电脑，先看学习和携带需求</h2>
          <p className="hero-card-lead">选课、查资料、整理作业时，先排出每天最常用的几件事。</p>
          <p className="hero-card-lead">
            选购 MateBook D 14 时，可结合课程软件、配置和携带需求，再核对对应型号的产品资料。
          </p>
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
              事实核验 5 项通过
            </span>
            <span className="pill warn">
              <i className="dot" />
              1 项待确认
            </span>
          </div>
        </aside>
      </section>

      <section className="landing-scenes" id="scenes">
        <div className="scenes-head">
          <h2>使用场景</h2>
          <p>根据读者与使用需求，调整文案内容。</p>
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
                  <span className="preview-title">参考资料（3）</span>
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
                    <span className="ver-now">当前版本</span>
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

      {recent.length > 0 ? (
        <section className="landing-recent">
          <div className="recent-head">
            <h2>最近作品</h2>
            <button type="button" className="btn ghost small" onClick={() => navigate("/history")}>
              全部历史
            </button>
          </div>
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
      ) : null}

      <footer className="landing-foot">
        <strong>懂你所需 · 营销内容工作台</strong>
        <span>产品资料、文案编辑与版本管理</span>
        <span>数据只存在本机的 SQLite；生成逻辑沿用现有 agent 流程，不接入新的模型或第三方服务。</span>
        <span className="credit">场景配图来自 Unsplash，遵循 Unsplash License，可商用、免署名。</span>
      </footer>
    </div>
  );
}
