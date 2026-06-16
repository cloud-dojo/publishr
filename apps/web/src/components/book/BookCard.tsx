import Link from "next/link";

import type { Book } from "@publishr/shared-schema";

import { coverSrc } from "@/data/config";

import { BookCover } from "./BookCover";
import { StatusBadge } from "./StatusBadge";
import { WhyBubble } from "./WhyBubble";

function hrefFor(book: Book): string {
  // 本を選んだら一旦「概要」へ（いきなり本文に飛ばさない）。なぜこの本か・目次・序文サンプルを
  // 見せ、概要の「いま読む」で /read へ。予約導線は無し（企画したら自動執筆済み）。
  return `/books/${book.id}`;
}

function authorSuffix(book: Book): string {
  if (book.status === "writing") return ` ・ 残り ${Math.max(0, 100 - book.feedback.readPercent)}%`;
  if (book.status === "draft" && book.shelf === "press") return " ・ 企画承認済み";
  if (book.status === "published" && book.feedback.rating) {
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
}: {
  book: Book;
  authorName: string;
  reason?: string;
  showWhy?: boolean;
  layout?: "grid" | "row";
}) {
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
          titleSize={13}
        />
        <div className="book-body">
          <div className="book-badges">
            <StatusBadge status={book.status} shelf={book.shelf} floating={false} />
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
        badge={<StatusBadge status={book.status} shelf={book.shelf} floating={false} />}
      />
      <div className="book-meta">
        <div className="bm-title">{book.title}</div>
        <div className="bm-author">
          {authorName} 著{authorSuffix(book)}
        </div>
      </div>
      {showWhy && reason ? <WhyBubble reason={reason} /> : null}
    </Link>
  );
}
