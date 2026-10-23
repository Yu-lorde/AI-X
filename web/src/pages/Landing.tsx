import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { ArrowIcon, MoonIcon, SparkIcon, SunIcon } from "../components/Icons";
import { useTheme } from "../theme";
import type { WorkSummary } from "../types";
import { formatTime } from "../utils";

const SCENES = [
  {
    img: "/media/campus.jpg",
    tag: "高校学生",
    title: "开学季 · 宿舍 · 课堂",
    body: "把轻薄、续航、屏幕这些参数，写成新生能感同身受的日常。",
  },
  {
    img: "/media/office.jpg",
    tag: "职场办公",
    title: "通勤 · 会议 · 移动办公",
    body: "围绕效率与协同，强调接口、重量和智慧办公体验。",
  },
  {
    img: "/media/creator.jpg",
    tag: "内容创作",
    title: "图文 · 种草 · 短视频脚本",
    body: "按平台模板组织开头、卖点与行动引导，配图位置一并给出。",
  },
];

const STEPS = [
  {
    no: "01",
    title: "写清这一篇要卖给谁",
    body: "产品型号、目标人群、业务场景、发布平台。四个字段决定了知识库检索范围和平台模板。",
  },
  {
    no: "02",
    title: "检索、生成、核验一次完成",
    body: "先读场景文档与产品事实，再按平台结构成稿；事实、配图型号与合规风险同时核验。",
  },
  {
    no: "03",
    title: "改到能直接发，版本留档",
    body: "左边改文字和配图，右边实时重排；每次保存都是一个新版本，随时可以回看。",
  },
];

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

  return (
    <div className="landing">
      <div className="landing-fluid" aria-hidden="true">
        <span className="blob blob-a" />
        <span className="blob blob-b" />
        <span className="blob blob-c" />
      </div>

      <header className="landing-head">
        <div className="landing-brand">
          <span className="brand-mark">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
              <path d="M12 2.6l2.1 5.7 5.7 2.1-5.7 2.1L12 18.2l-2.1-5.7L4.2 10.4l5.7-2.1z" />
            </svg>
          </span>
          <span>
            <strong>AI+X</strong>
            <small>营销软文工作台</small>
          </span>
        </div>
        <div className="landing-head-actions">
          <button type="button" className="icon-btn" onClick={toggle} title="切换日间 / 夜间">
            {theme === "light" ? <MoonIcon size={16} /> : <SunIcon size={16} />}
          </button>
          <button type="button" className="btn ghost" onClick={() => navigate("/history")}>
            历史作品
          </button>
        </div>
      </header>

      <main className="landing-main">
        <section className="hero">
          <p className="eyebrow reveal">
            <i />
            HUAWEI PC · 内容中台
          </p>
          <h1 className="reveal">
            把一条需求，写成
            <br />
            能直接发布的<b>营销软文</b>
          </h1>
          <p className="hero-sub reveal">
            选好人群、场景与平台，系统先查本地知识库，再按平台模板成稿，并自动核验产品事实、配图型号与合规风险。改文字即时重排，每次保存都留一个版本。
          </p>
          <div className="hero-actions reveal">
            <button type="button" className="btn primary xl" onClick={() => navigate("/workspace")}>
              <SparkIcon size={17} />
              开始创作
            </button>
            <button type="button" className="btn ghost xl" onClick={() => navigate("/history")}>
              看看生成过的稿子
              <ArrowIcon size={15} />
            </button>
          </div>
          <ul className="hero-facts reveal">
            <li>
              <b>8</b>
              <span>业务场景</span>
            </li>
            <li>
              <b>13</b>
              <span>发布平台</span>
            </li>
            <li>
              <b>V1·V2…</b>
              <span>改动可回溯</span>
            </li>
          </ul>
        </section>

        <aside className="hero-card reveal" aria-hidden="true">
          <div className="hero-card-top">
            <span className="chip subtle">小红书</span>
            <span className="chip">开学季</span>
            <span className="hero-dot" />
          </div>
          <h2>大学新生必备：MateBook D 14 的轻便体验</h2>
          <p className="hero-card-lead">
            新学期开始，一台轻便且性能出色的笔记本是大学生活的好帮手。从教室到图书馆，一台就够。
          </p>
          <div className="hero-figure">
            <span className="hero-line w80" />
            <span className="hero-line w95" />
            <span className="hero-line w70" />
            <span className="hero-line w88" />
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
      </main>

      <section className="landing-scenes">
        <div className="scenes-head">
          <h2>已经适配的场景</h2>
          <p>同一套知识库，按人群和平台换不同的写法与配图。</p>
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
        {STEPS.map((step) => (
          <article key={step.no} className="step-card">
            <span className="step-no">{step.no}</span>
            <h3>{step.title}</h3>
            <p>{step.body}</p>
          </article>
        ))}
      </section>

      {recent.length > 0 ? (
        <section className="landing-recent">
          <div className="recent-head">
            <h2>接着上次继续</h2>
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
        <span>数据只存在本机的 SQLite；生成逻辑沿用现有 agent 流程，不接入新的模型或第三方服务。</span>
        <span className="credit">场景配图来自 Unsplash，遵循 Unsplash License，可商用、免署名。</span>
      </footer>
    </div>
  );
}
