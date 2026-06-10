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
  // coverUrl（実Imagen等の表紙画像）があれば画像を表示。無ければ CSS バリアントの装丁。
  if (coverUrl) {
    return (
      <div className="cover cover--image">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={coverUrl} alt={title} className="cover-img" />
        {badge ? <div className="cover-badge">{badge}</div> : null}
      </div>
    );
  }
  const titleStyle: CSSProperties | undefined = titleSize
    ? { fontSize: `${titleSize}px` }
    : undefined;
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
