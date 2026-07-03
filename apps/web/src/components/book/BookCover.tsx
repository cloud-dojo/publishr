import type { CSSProperties, ReactNode } from "react";

import { simpleCoverFallback } from "@/data/config";

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
  // ⚠️ DORMANT: 表紙の画像生成（Imagen）は今回スコープ外で park。現行 coverUrl は常に null のため
  // この分岐は現状使われず、下の CSS variant フォールバックが常用される。将来の画像生成再結線用に温存。
  // coverUrl（実Imagen等の文字なしアイコン装画）があれば最優先で「上＝固定タイトル帯／下＝アイコン装画」
  // の2段に組む（日本語タイトルは Imagen で焼けないため UI 側で上段に重ねる）。imagen が無いときに
  // 簡易表紙/CSS装丁へフォールバックする。
  if (coverUrl) {
    return (
      <div className="cover cover--image">
        <div className="cover-overlay">
          <div className="c-title" style={titleStyle}>
            {title}
          </div>
          {subtitle ? <div className="c-sub">{subtitle}</div> : null}
          {author ? <div className="c-author">{author}</div> : null}
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={coverUrl} alt={title} className="cover-img" />
        {badge ? <div className="cover-badge">{badge}</div> : null}
      </div>
    );
  }
  // 簡易表紙（既定・imagen 未連携時）。画像/サブ/著者/装飾を捨て、variant 由来のシックな暗色グラデ＋
  // タイトル左上だけのミニマル装丁にする（色は variant でばらける）。NEXT_PUBLIC_SIMPLE_COVER=0 で無効化。
  if (simpleCoverFallback) {
    return (
      <div className={`cover cover--${variant || "b1"} cover-min`}>
        <div className="c-title" style={titleStyle}>
          {title}
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
