import Link from "next/link";

import type { Book } from "@publishr/shared-schema";

import { coverSrc } from "@/data/config";
import { shelfExpiryLabel } from "@/lib/arrival";

import { BookCover } from "./BookCover";
import { StatusBadge } from "./StatusBadge";
import { WhyBubble } from "./WhyBubble";

function hrefFor(book: Book): string {
  // 本を選んだら一旦「概要」へ（いきなり本文に飛ばさない）。なぜこの本か・目次・序文サンプルを
  // 見せ、概要の「いま読む」で /read へ。予約導線は無し（企画したら自動執筆済み）。
  return `/books/${book.id}`;
}

function authorSuffix(book: Book): string {
  // 配本時に本文まで生成済み＝published 前提。読了評価があれば ★ を添える（feedback 未設定は無印）。
  if (book.status === "published" && book.feedback?.rating) {
    return ` ・ ${"★".repeat(book.feedback.rating)}`;
  }
  return "";
}

export function BookCard({
  book,
  authorName,
  reason,
  showWhy = false,
  layout = "grid",
  showArrived = true,
  badgeMode = "arrival",
}: {
  book: Book;
  authorName: string;
  reason?: string;
  showWhy?: boolean;
  layout?: "grid" | "row";
  // 書庫では入荷日を出さない（showArrived=false）。バッジは読書進捗(progress)に切替。
  showArrived?: boolean;
  badgeMode?: "arrival" | "progress";
}) {
  const expiryLabel = shelfExpiryLabel(book.createdAt);

  // 横長レイアウト（書店トップ）：カバー左＋本文右にタグ・タイトル・著者・なぜカード
  if (layout === "row") {
    return (
      <Link className="book book--row reveal" href={hrefFor(book)}>
        <BookCover
          variant={book.coverVariant}
          coverUrl={coverSrc(book.id, book.coverUrl)}
          title={book.title}
          subtitle={book.subtitle}
          author={authorName}
          titleSize={10}
        />
        <div className="book-body">
          <div className="book-badges">
            {expiryLabel && (
              <span className="bm-arrived bm-arrived--expiry" title={`棚に並んだ日: ${book.createdAt?.slice(0, 10)}`}>
                {expiryLabel}
              </span>
            )}
          </div>
          <div className="bm-title">{book.title}</div>
          <div className="bm-author">
            {authorName} 著{authorSuffix(book)}
          </div>
          {showWhy && reason ? <WhyBubble reason={reason} /> : null}
        </div>
      </Link>
    );
  }

  // 縦レイアウト（既定：書庫・著者ページ）
  return (
    <Link className="book reveal" href={hrefFor(book)}>
      <BookCover
        variant={book.coverVariant}
        coverUrl={coverSrc(book.id, book.coverUrl)}
        title={book.title}
        subtitle={book.subtitle}
        author={authorName}
        badge={<StatusBadge book={book} floating={false} mode={badgeMode} />}
      />
      <div className="book-meta">
        <div className="bm-title">{book.title}</div>
        <div className="bm-author">
          {authorName} 著{authorSuffix(book)}
        </div>
        {showArrived && expiryLabel && (
          <div className="bm-arrived bm-arrived--expiry" title={`棚に並んだ日: ${book.createdAt?.slice(0, 10)}`}>
            {expiryLabel}
          </div>
        )}
      </div>
      {showWhy && reason ? <WhyBubble reason={reason} /> : null}
    </Link>
  );
}

