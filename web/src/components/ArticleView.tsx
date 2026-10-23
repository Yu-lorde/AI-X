import { Fragment } from "react";

import type { Article, PreviewImage } from "../types";
import { ImageIcon } from "./Icons";

function slotOf(position: string, count: number): number | null {
  if (/标题|导语|开头|封面|首图/.test(position)) return 0;
  if (/结尾|引导|文末/.test(position)) return count;
  const digits = position.match(/\d+/);
  if (!digits) return null;
  const index = Number(digits[0]);
  if (count === 0) return 0;
  return Math.min(Math.max(index, 1), count);
}

function Figures({ images }: { images: PreviewImage[] }) {
  if (!images.length) return null;
  return (
    <>
      {images.map((image, index) => (
        <figure className="article-figure" key={`${image.name}-${index}`}>
          {image.url ? (
            <img src={image.url} alt={image.caption || image.name} loading="lazy" />
          ) : (
            <div className="figure-placeholder">
              <ImageIcon size={22} />
              <span>配图暂不可用</span>
            </div>
          )}
          <figcaption>{image.caption}</figcaption>
        </figure>
      ))}
    </>
  );
}

export function ArticleView({ article }: { article: Article }) {
  const count = article.paragraphs.length;
  const slots: PreviewImage[][] = Array.from({ length: count + 1 }, () => []);
  const loose: PreviewImage[] = [];
  article.images.forEach((image) => {
    const slot = slotOf(image.position, count);
    if (slot === null) loose.push(image);
    else slots[slot].push(image);
  });
  loose.forEach((image, index) => slots[Math.min(index + 1, count)].push(image));

  return (
    <article className="article">
      <h1 data-anchor="title">{article.title || "未命名"}</h1>
      {article.lead ? (
        <p className="article-lead" data-anchor="lead">
          {article.lead}
        </p>
      ) : null}
      <Figures images={slots[0]} />
      {article.paragraphs.map((paragraph, index) => (
        <Fragment key={index}>
          {paragraph.trim() ? <p data-anchor={`p${index}`}>{paragraph}</p> : null}
          <Figures images={slots[index + 1]} />
        </Fragment>
      ))}
      {article.cta ? (
        <p className="article-cta" data-anchor="cta">
          {article.cta}
        </p>
      ) : null}
      {article.tags.length > 0 ? (
        <p className="article-tags">{article.tags.map((tag) => `#${tag.replace(/^#/, "")}`).join(" ")}</p>
      ) : null}
    </article>
  );
}
