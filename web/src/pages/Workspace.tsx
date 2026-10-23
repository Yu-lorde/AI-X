import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api";
import { EditorPanel } from "../components/EditorPanel";
import { EmptyState } from "../components/EmptyState";
import { PlusIcon, SaveIcon, SparkIcon } from "../components/Icons";
import { PreviewPanel } from "../components/PreviewPanel";
import type { Editor, GenerateFailure, Inputs, Meta, Preview, WorkData } from "../types";

const FALLBACK_SCENES = ["开学季", "职场办公", "内容创作", "家庭换新", "企业采购", "门店到访", "新品首发", "节日营销"];
const FALLBACK_PLATFORMS = [
  "微信公众号",
  "小红书",
  "销售朋友圈",
  "门店海报",
  "知乎",
  "微博",
  "新闻稿",
  "抖音短视频",
  "微信视频号",
  "B站中长视频",
  "短视频口播",
  "直播讲解",
  "企业采购方案",
];
const DEFAULT_INPUTS: Inputs = { product: "", audience: "", scene: "开学季", platform: "小红书", note: "" };

const errorText = (error: unknown) => (error instanceof Error ? error.message : "操作失败，请稍后重试。");

export function WorkspacePage() {
  const { workId } = useParams();
  const navigate = useNavigate();

  const [sentence, setSentence] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseHint, setParseHint] = useState("");
  const [meta, setMeta] = useState<Meta | null>(null);
  const [form, setForm] = useState<Inputs>(DEFAULT_INPUTS);
  const [work, setWork] = useState<WorkData | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formOpen, setFormOpen] = useState(true);
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState<string[]>([]);
  const [notice, setNotice] = useState("");

  const skipLoad = useRef<string | null>(null);
  const previewSeq = useRef(0);
  const editorScroll = useRef<HTMLDivElement | null>(null);
  const previewScroll = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const left = editorScroll.current;
    const right = previewScroll.current;
    if (!left || !right) return;

    type Anchor = { key: string; top: number };
    const READ_LINE = 14;

    // 只跟随“用户真正操作过的那一侧”，避免程序化滚动回写触发对方的 scroll 事件形成回路
    let userSide: "left" | "right" | null = null;
    let frame = 0;
    let dirty = true;

    const collect = (el: HTMLDivElement): Anchor[] => {
      const base = el.getBoundingClientRect().top - el.scrollTop;
      return Array.from(el.querySelectorAll<HTMLElement>("[data-anchor]"))
        .map((node) => ({ key: node.dataset.anchor || "", top: node.getBoundingClientRect().top - base }))
        .filter((item) => item.key);
    };

    let leftAnchors = collect(left);
    let rightAnchors = collect(right);

    const refresh = () => {
      leftAnchors = collect(left);
      rightAnchors = collect(right);
      dirty = false;
    };

    // 阅读线落在哪两个锚点之间，图片撑高的区间会让跟随侧按比例走得更快
    const segmentOf = (anchors: Anchor[], read: number) => {
      if (!anchors.length) return null;
      let index = 0;
      for (let i = 0; i < anchors.length; i += 1) {
        if (anchors[i].top <= read) index = i;
        else break;
      }
      const lower = index === anchors.length - 1 ? Math.max(index - 1, 0) : index;
      const upper = Math.min(lower + 1, anchors.length - 1);
      if (lower === upper) return { a: anchors[lower], b: anchors[lower], ratio: 0 };
      const span = Math.max(anchors[upper].top - anchors[lower].top, 1);
      return { a: anchors[lower], b: anchors[upper], ratio: (read - anchors[lower].top) / span };
    };

    const sync = (from: HTMLDivElement, to: HTMLDivElement, fromAnchors: Anchor[], toAnchors: Anchor[]) => {
      // 只按两侧都存在的锚点分段，缺失的段落不会让跟随中断
      const keys = new Set(toAnchors.map((item) => item.key));
      const usable = fromAnchors.filter((item) => keys.has(item.key));
      const segment = segmentOf(usable, from.scrollTop + READ_LINE);
      if (!segment) return;
      const a = toAnchors.find((item) => item.key === segment.a.key);
      const b = toAnchors.find((item) => item.key === segment.b.key) ?? a;
      if (!a || !b) return;
      const next = a.top + segment.ratio * (b.top - a.top) - READ_LINE;
      const max = Math.max(to.scrollHeight - to.clientHeight, 0);
      aim(to, Math.min(Math.max(next, 0), max));
    };

    // 目标位置逐帧逼近，图片区间需要多滚的距离会被摊到几帧里，不会一帧跳过去
    let aimEl: HTMLDivElement | null = null;
    let aimTo = 0;
    let glide = 0;

    const glideStep = () => {
      glide = 0;
      if (!aimEl) return;
      const remaining = aimTo - aimEl.scrollTop;
      if (Math.abs(remaining) < 0.5) {
        aimEl = null;
        return;
      }
      aimEl.scrollTop += Math.max(Math.min(remaining * 0.45, 120), -120);
      glide = requestAnimationFrame(glideStep);
    };

    const aim = (el: HTMLDivElement, value: number) => {
      aimEl = el;
      aimTo = value;
      if (!glide) glide = requestAnimationFrame(glideStep);
    };

    const stopGlide = () => {
      aimEl = null;
      if (glide) {
        cancelAnimationFrame(glide);
        glide = 0;
      }
    };

    const run = () => {
      frame = 0;
      if (!userSide) return;
      if (dirty) refresh();
      if (userSide === "left") sync(left, right, leftAnchors, rightAnchors);
      else sync(right, left, rightAnchors, leftAnchors);
    };

    const arm = (side: "left" | "right") => () => {
      if (userSide !== side) return;
      if (!frame) frame = requestAnimationFrame(run);
    };

    const onLeft = arm("left");
    const onRight = arm("right");
    const takeLeft = () => {
      if (userSide === "left") return;
      stopGlide();
      userSide = "left";
    };
    const takeRight = () => {
      if (userSide === "right") return;
      stopGlide();
      userSide = "right";
    };

    const bind = (el: HTMLDivElement, take: () => void) => {
      el.addEventListener("wheel", take, { passive: true });
      el.addEventListener("pointerdown", take, { passive: true });
      el.addEventListener("touchstart", take, { passive: true });
      el.addEventListener("focusin", take);
      const onLoad = () => {
        dirty = true;
      };
      el.addEventListener("load", onLoad, true);
      return () => {
        el.removeEventListener("wheel", take);
        el.removeEventListener("pointerdown", take);
        el.removeEventListener("touchstart", take);
        el.removeEventListener("focusin", take);
        el.removeEventListener("load", onLoad, true);
      };
    };

    left.addEventListener("scroll", onLeft, { passive: true });
    right.addEventListener("scroll", onRight, { passive: true });
    const unbindLeft = bind(left, takeLeft);
    const unbindRight = bind(right, takeRight);

    // 文字、图片、视口变化后重新测量锚点位置，滚动过程中不再反复读取布局
    const observer = new MutationObserver(() => {
      dirty = true;
    });
    observer.observe(left, { childList: true, subtree: true, characterData: true });
    observer.observe(right, { childList: true, subtree: true, characterData: true });
    const onResize = () => {
      dirty = true;
    };
    window.addEventListener("resize", onResize);

    return () => {
      left.removeEventListener("scroll", onLeft);
      right.removeEventListener("scroll", onRight);
      unbindLeft();
      unbindRight();
      if (frame) cancelAnimationFrame(frame);
      stopGlide();
      observer.disconnect();
      window.removeEventListener("resize", onResize);
    };
  }, [work?.work_id, loading, Boolean(work)]);

  const applyWork = useCallback((data: WorkData) => {
    setWork(data);
    setEditor(data.editor);
    setPreview(data.preview);
    setForm(data.inputs);
    setQuestions([]);
  }, []);

  useEffect(() => {
    api
      .meta()
      .then(setMeta)
      .catch(() => setMeta(null));
  }, []);

  const loadWork = useCallback(
    async (id: string) => {
      setLoading(true);
      setError("");
      try {
        applyWork(await api.work(id));
      } catch (err) {
        setError(errorText(err));
      } finally {
        setLoading(false);
      }
    },
    [applyWork],
  );

  useEffect(() => {
    if (!workId) return;
    if (work?.work_id === workId) return;
    if (skipLoad.current === workId) {
      skipLoad.current = null;
      return;
    }
    void loadWork(workId);
  }, [workId, work?.work_id, loadWork]);

  useEffect(() => {
    if (!work?.work_id || !editor || loading) return;
    const seq = ++previewSeq.current;
    const timer = window.setTimeout(() => {
      api
        .preview(work.work_id, editor)
        .then((data) => {
          if (previewSeq.current === seq) setPreview(data);
        })
        .catch(() => {});
    }, 500);
    return () => window.clearTimeout(timer);
  }, [editor, work?.work_id, loading]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 3200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const dirty = Boolean(preview && work && preview.fingerprint !== work.saved_fingerprint);

  const update = (part: Partial<Inputs>) => setForm((current) => ({ ...current, ...part }));

  const onParse = async () => {
    if (parsing || busy || !sentence.trim()) return;
    setParsing(true);
    setParseHint("");
    try {
      const { inputs } = await api.parseRequest(sentence);
      setForm(current => ({ ...current, ...inputs, perspective: inputs.perspective || current.perspective || meta?.perspective_default }));
      const missing = [!inputs.product && "产品型号", !inputs.platform && "发布平台"].filter(Boolean);
      setParseHint(missing.length ? `已解析，请补充${missing.join("、")}；核对下方字段后再生成。` : "已填入下方字段，请核对后生成。人群和场景可留空。");
    } catch (error) { setParseHint(errorText(error)); }
    finally { setParsing(false); }
  };

  const onGenerate = async () => {
    if (busy || parsing) return;
    if (!form.product.trim() || !form.platform.trim()) {
      setError("先填写产品型号和发布平台，再生成。");
      setFormOpen(true);
      return;
    }
    setBusy(true);
    setError("");
    setQuestions([]);
    setNotice("");
    try {
      const data = await api.generate(form);
      if (!data.ok) {
        const failure = data as GenerateFailure;
        setError([failure.message, failure.detail].filter(Boolean).join(" ") || "未能生成");
        setQuestions(failure.questions || []);
        return;
      }
      const result = data as WorkData;
      applyWork(result);
      setFormOpen(false);
      setNotice(result.warning || "成稿已生成，并自动保存为 V1");
      if (result.work_id) {
        skipLoad.current = result.work_id;
        navigate(`/workspace/${result.work_id}`, { replace: true });
      }
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const onSave = async () => {
    if (!work || !editor || saving) return;
    setSaving(true);
    setError("");
    try {
      const data = await api.saveVersion(work.work_id, editor, work.version_no);
      setWork(data);
      setEditor(data.editor);
      setPreview(data.preview);
      setNotice(data.message || "已保存");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  };

  const onSwitchVersion = async (value: string) => {
    if (!work) return;
    const versionNo = Number(value);
    if (versionNo === work.version_no) return;
    if (dirty && !window.confirm("当前有未保存修改，切换版本会放弃这些修改，继续吗？")) return;
    setLoading(true);
    setError("");
    try {
      applyWork(await api.work(work.work_id, versionNo));
      setNotice(`已切换到 V${versionNo}`);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  };

  const onNew = () => {
    setWork(null);
    setEditor(null);
    setPreview(null);
    setForm(DEFAULT_INPUTS);
    setFormOpen(true);
    setError("");
    setQuestions([]);
    setNotice("");
    if (workId) navigate("/workspace");
  };

  const startExample = (inputs: Inputs) => {
    setForm(inputs);
    setFormOpen(true);
    setError("");
  };

  const scenes = meta?.scenes ?? FALLBACK_SCENES;
  const platforms = meta?.platforms ?? FALLBACK_PLATFORMS;

  return (
    <div className="page workspace-page">
      <header className="page-head">
        <div>
          <h1>{work ? "创作工作台" : "开始一篇新的营销软文"}</h1>
          <p className="page-sub">
            {work
              ? "左侧改文字和配图，右侧实时更新成稿；满意后保存为新版本。"
              : "选好人群、场景与平台，系统按知识库和平台模板生成并核验。"}
          </p>
        </div>
        <div className="head-actions">
          <span className={`pill ${meta?.kb.exists ? "ok" : "warn"}`}>
            <i className="dot" />
            {meta?.source_hint || "本地知识库"}
          </span>
          {work ? (
            <button type="button" className="btn ghost" onClick={onNew}>
              <PlusIcon size={15} />
              新建创作
            </button>
          ) : null}
        </div>
      </header>

      {!formOpen && work ? (
        <div className="task-summary">
          <div className="chips">
            <span className="chip strong">{work.inputs.product}</span>
            <span className="chip">{work.inputs.audience}</span>
            <span className="chip">{work.inputs.scene}</span>
            <span className="chip">{work.inputs.platform}</span>
            {work.inputs.note ? <span className="chip subtle">补充：{work.inputs.note}</span> : null}
          </div>
          <button type="button" className="btn ghost small" onClick={() => setFormOpen(true)}>
            修改任务
          </button>
        </div>
      ) : (
        <section className="card task-card">
          <div className="sentence-demand field">
            <label htmlFor="sentence-demand">一句话需求</label>
            <textarea id="sentence-demand" rows={2} value={sentence} disabled={parsing || busy}
              onChange={e => setSentence(e.target.value)}
              placeholder="例如：以真实用户视角给开学季大学新生写一篇小红书，推荐 MateBook D 14，重点讲便携。" />
            <div className="sentence-demand-actions">
              <span className="hint" role="status">{parseHint || "解析后自动填写下方字段，可继续手动修改。"}</span>
              <button type="button" className="btn ghost" disabled={parsing || busy || !sentence.trim()} onClick={onParse}>{parsing ? "正在解析…" : "解析填入"}</button>
            </div>
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="f-product">产品型号</label>
              <input
                id="f-product"
                placeholder="例如 MateBook D 14"
                value={form.product}
                onChange={(event) => update({ product: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="f-audience">目标人群（可留空）</label>
              <input
                id="f-audience"
                placeholder="例如 大学新生"
                value={form.audience}
                onChange={(event) => update({ audience: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="f-scene">业务场景</label>
              <select id="f-scene" value={form.scene} onChange={(event) => update({ scene: event.target.value })}>
                <option value="">无明确场景</option>
                {scenes.map((scene) => (
                  <option key={scene}>{scene}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="f-platform">发布平台</label>
              <select
                id="f-platform"
                value={form.platform}
                onChange={(event) => update({ platform: event.target.value })}
              >
                <option value="">请选择平台</option>
                {platforms.map((platform) => (
                  <option key={platform}>{platform}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="f-perspective">写作视角</label>
              <select id="f-perspective" value={form.perspective || meta?.perspective_default || ""} onChange={e => update({ perspective: e.target.value })}>
                {!meta?.perspectives?.length && <option value="">默认视角</option>}
                {meta?.perspectives?.map(item => <option key={item} value={item}>{item}</option>)}
              </select>
            </div>
            <div className="field wide">
              <label htmlFor="f-note">临时修改要求</label>
              <input
                id="f-note"
                placeholder="例如 删掉续航，只保留携带"
                value={form.note}
                onChange={(event) => update({ note: event.target.value })}
              />
            </div>
          </div>
          <div className="task-actions">
            <span className="hint">生成会先检索知识库再调用大模型，通常需要几十秒。</span>
            <div className="task-buttons">
              {work ? (
                <button type="button" className="btn ghost small" onClick={() => setFormOpen(false)}>
                  收起
                </button>
              ) : null}
              <button type="button" className="btn primary" onClick={onGenerate} disabled={busy}>
                <SparkIcon size={16} />
                {busy ? "正在生成…" : "生成并核验"}
              </button>
            </div>
          </div>
        </section>
      )}

      {error ? (
        <div className="banner error">
          <strong>没能完成</strong>
          <p>{error}</p>
          {questions.length ? (
            <ul>
              {questions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {notice ? <div className="toast">{notice}</div> : null}

      {busy ? (
        <div className="loading-card">
          <span className="spinner" />
          <div>
            <strong>正在生成成稿</strong>
            <p>依次检索场景文档、平台模板与产品事实，再写入并核验。请保持页面打开。</p>
          </div>
        </div>
      ) : null}

      {loading ? <div className="loading-card"><span className="spinner" /><div><strong>正在载入</strong><p>读取历史版本与配图。</p></div></div> : null}

      {!work && !busy && !loading ? <EmptyState onExample={startExample} /> : null}

      {work && !loading ? (
        <>
          <div className="work-head">
            <div className="work-title">
              <h2>{editor?.title || work.title || "未命名"}</h2>
              <div className="work-meta-row">
                <span className="chip subtle">{work.inputs.platform}</span>
                <span className={`save-state${dirty ? " dirty" : ""}`}>
                  {dirty ? "有未保存修改" : `已保存 V${work.saved_version_no}`}
                </span>
                {work.warning ? <span className="save-state dirty">{work.warning}</span> : null}
              </div>
            </div>
            <div className="work-actions">
              {work.versions.length > 1 ? (
                <label className="version-pick">
                  版本
                  <select value={work.version_no} onChange={(event) => void onSwitchVersion(event.target.value)}>
                    {work.versions.map((version) => (
                      <option key={version.version_no} value={version.version_no}>
                        V{version.version_no}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <button type="button" className="btn primary" onClick={onSave} disabled={saving || !dirty}>
                <SaveIcon size={15} />
                {saving ? "保存中…" : "保存新版本"}
              </button>
            </div>
          </div>

          <div className="split">
            <section className="card panel">
              <div className="panel-head">
                <h3>编辑区</h3>
                <span className="hint">{editor?.paragraphs.length ?? 0} 段正文</span>
              </div>
              <div className="panel-meta">
                <span className="meta-scene">改动自动同步到右侧</span>
                <span className="meta-options">保存新版本后才写入历史</span>
              </div>
              {editor ? (
                <EditorPanel
                  editor={editor}
                  candidates={work.candidates}
                  useTags={work.meta.use_tags}
                  missingImages={work.missing_images}
                  onChange={setEditor}
                  scrollRef={editorScroll}
                />
              ) : null}
            </section>
            <section className="card panel">
              <PreviewPanel preview={preview ?? work.preview} meta={work.meta} scrollRef={previewScroll} />
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
