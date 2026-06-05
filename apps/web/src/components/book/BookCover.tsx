import type { CSSProperties, ReactNode } from "react";

export function BookCover({
  variant,
  title,
  subtitle,
  author,
  titleSize,
  badge,
}: {
  variant: string;
  title: string;
  subtitle?: string | null;
  author?: string | null;
  titleSize?: number;
  badge?: ReactNode;
}) {
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
