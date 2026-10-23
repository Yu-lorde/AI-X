import { useMemo, useState, type RefObject } from "react";

import type { Candidate, Editor } from "../types";
import { ImageIcon } from "./Icons";

interface Props {
  editor: Editor;
  candidates: Candidate[];
  useTags: boolean;
  missingImages: string[];
  onChange: (editor: Editor) => void;
  scrollRef?: RefObject<HTMLDivElement | null>;
}

const NONE = "";

export function EditorPanel({ editor, candidates, useTags, missingImages, onChange, scrollRef }: Props) {
  const [focus, setFocus] = useState(-1);
  const count = editor.paragraphs.length;

  const slots = useMemo(
    () => [
      { value: -1, label: "封面" },
      ...editor.paragraphs.map((_, index) => ({ value: index, label: `第${index + 1}段后` })),
    ],
    [count],
  );

  const patch = (part: Partial<Editor>) => onChange({ ...editor, ...part });

  const setParagraph = (index: number, value: string) => {
    const paragraphs = [...editor.paragraphs];
    paragraphs[index] = value;
    patch({ paragraphs });
  };

  const assign = (slot: number, name: string) => {
    const item = candidates.find((candidate) => candidate.name === name);
    const caption = item?.theme || "";
    if (slot < 0) {
      patch({ cover: name, cover_caption: caption });
      return;
    }
    const picks = [...editor.picks];
    const captions = [...editor.captions];
    picks[slot] = name;
    captions[slot] = caption;
    patch({ picks, captions });
  };

  return (
    <div className="editor-scroll" ref={scrollRef}>
      <div className="field" data-anchor="title">
        <label htmlFor="ed-title">标题</label>
        <textarea
          id="ed-title"
          rows={2}
          value={editor.title}
          onChange={(event) => patch({ title: event.target.value })}
        />
      </div>

      <div className="field">
        <label htmlFor="ed-options">
          标题备选 <span className="hint">一行一个，最多 3 个</span>
        </label>
        <textarea
          id="ed-options"
          rows={3}
          value={editor.options}
          onChange={(event) => patch({ options: event.target.value })}
        />
      </div>

      <div className="field" data-anchor="lead">
        <label htmlFor="ed-lead">导语</label>
        <textarea id="ed-lead" rows={3} value={editor.lead} onChange={(event) => patch({ lead: event.target.value })} />
      </div>

      <div className="divider" />

      <div className="section-label">封面与备选图片</div>
      <div className="pair">
        <div className="field">
          <label htmlFor="ed-cover">封面图</label>
          <select
            id="ed-cover"
            value={editor.cover}
            onChange={(event) => assign(-1, event.target.value)}
          >
            <option value={NONE}>不配图</option>
            {candidates.map((item) => (
              <option key={item.name} value={item.name}>
                {item.theme || item.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ed-cover-cap">封面说明</label>
          <input
            id="ed-cover-cap"
            value={editor.cover_caption}
            onChange={(event) => patch({ cover_caption: event.target.value })}
          />
        </div>
      </div>

      {candidates.length > 0 ? (
        <div className="gallery-box">
          <div className="gallery-head">
            <span className="hint">先在右侧选位置，再点图片替换</span>
            <select value={focus} onChange={(event) => setFocus(Number(event.target.value))}>
              {slots.map((slot) => (
                <option key={slot.value} value={slot.value}>
                  替换到：{slot.label}
                </option>
              ))}
            </select>
          </div>
          <div className="gallery">
            {candidates.map((item) => {
              const active = focus < 0 ? editor.cover === item.name : editor.picks[focus] === item.name;
              return (
                <button
                  key={item.name}
                  type="button"
                  className={`thumb${active ? " active" : ""}${item.missing ? " missing" : ""}`}
                  title={`${item.name}${item.theme ? ` · ${item.theme}` : ""}`}
                  onClick={() => assign(focus, item.name)}
                >
                  {item.url ? <img src={item.url} alt={item.name} loading="lazy" /> : <ImageIcon size={20} />}
                  <span>{item.theme || item.name}</span>
                </button>
              );
            })}
          </div>
          {missingImages.length > 0 ? (
            <p className="warning-text">这些图片在本机已不可用：{missingImages.join("、")}</p>
          ) : null}
        </div>
      ) : (
        <p className="hint">本次知识库没有返回可用图片。</p>
      )}

      <div className="divider" />

      <div className="section-label">正文</div>
      {editor.paragraphs.map((paragraph, index) => (
        <div className="para-block" key={index} data-anchor={`p${index}`}>
          <div className="para-head">
            <span className="para-no">{index + 1}</span>
            <span>第 {index + 1} 段</span>
          </div>
          <textarea rows={4} value={paragraph} onChange={(event) => setParagraph(index, event.target.value)} />
          <div className="pair">
            <div className="field">
              <label htmlFor={`ed-pick-${index}`}>段后配图</label>
              <select
                id={`ed-pick-${index}`}
                value={editor.picks[index] || ""}
                onChange={(event) => assign(index, event.target.value)}
              >
                <option value={NONE}>不配图</option>
                {candidates.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor={`ed-cap-${index}`}>配图说明</label>
              <input
                id={`ed-cap-${index}`}
                value={editor.captions[index] || ""}
                onChange={(event) => {
                  const captions = [...editor.captions];
                  captions[index] = event.target.value;
                  patch({ captions });
                }}
              />
            </div>
          </div>
        </div>
      ))}

      <div className="divider" />

      <div className="field" data-anchor="cta">
        <label htmlFor="ed-cta">行动引导</label>
        <textarea id="ed-cta" rows={2} value={editor.cta} onChange={(event) => patch({ cta: event.target.value })} />
      </div>

      {useTags ? (
        <div className="field">
          <label htmlFor="ed-tags">标签</label>
          <input id="ed-tags" value={editor.tags} onChange={(event) => patch({ tags: event.target.value })} />
        </div>
      ) : null}
    </div>
  );
}
