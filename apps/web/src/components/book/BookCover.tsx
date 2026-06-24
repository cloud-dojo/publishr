import type { CSSProperties, ReactNode } from "react";

export function BookCover({
  variant,
  coverUrl,
  title,
  subtitle,
  author,
  titleSize,
  badge,
}: {
  variant: string;
  coverUrl?: string | null;
  title: string;
  subtitle?: string | null;
  author?: string | null;
  titleSize?: number;
  badge?: ReactNode;
}) {
  const titleStyle: CSSProperties | undefined = titleSize
    ? { fontSize: `${titleSize}px` }
    : undefined;
  // coverUrl（実Imagen等の文字なし装画）があれば画像を背景に敷き、その上に実タイトル/副題/著者を重畳する
  // （日本語タイトルは Imagen で焼けないため UI 側で重ねる＝ベストセラー装丁＋くっきり日本語）。無ければ CSS 装丁。
  if (coverUrl) {
    return (
      <div className="cover cover--image">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={coverUrl} alt={title} className="cover-img" />
        <div className="cover-scrim" />
        <div className="cover-overlay">
          <div className="c-title" style={titleStyle}>
            {title}
          </div>
          {subtitle ? <div className="c-sub">{subtitle}</div> : null}
          {author ? <div className="c-author">{author}</div> : null}
        </div>
        {badge ? <div className="cover-badge">{badge}</div> : null}
      </div>
    );
  }
  return (
    <div className={`cover cover--${variant}`}>
      <div className="c-title" style={titleStyle}>
        {title}
      </div>
      <div className="c-rule" />
      {subtitle ? <div className="c-sub">{subtitle}</div> : null}
      {author ? <div className="c-author">{author}</div> : null}
      {badge ? <div className="cover-badge">{badge}</div> : null}
    </div>
  );
}
