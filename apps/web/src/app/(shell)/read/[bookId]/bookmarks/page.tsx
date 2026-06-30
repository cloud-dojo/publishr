"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { BackLink } from "@/components/shell/NavigationHistory";
import { chapterForPara } from "@/data/bookText";
import { useProvider } from "@/data/hooks";

export default function BookBookmarksPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const book = provider.getBook(params.bookId);

  if (!book) {
    return (
      <>
        <header className="topbar">
          <div className="reader-top">
            <BackLink href={`/read/${params.bookId}`} className="greeting">‹ 本へ戻る</BackLink>
          </div>
        </header>
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const bookmarks = (book.annotations ?? [])
    .filter((a) => a.kind === "bookmark")
    .slice()
    .sort((a, b) => a.paragraphIndex - b.paragraphIndex);

  return (
    <>
      <header className="topbar">
        <div className="reader-top">
          <BackLink href={`/read/${book.id}`} className="greeting">‹ 本へ戻る</BackLink>
          <div className="rt-title">
            {book.title} <span>／ {persona?.name}</span>
          </div>
        </div>
      </header>

      <div className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Your bookmarks</div>
            <div className="section-title">
              ブックマーク <span className="group-count">{bookmarks.length}件</span>
            </div>
            <div className="section-sub">タップすると本文の該当ページへ移動します。</div>
          </div>
        </div>

        {bookmarks.length === 0 ? (
          <div className="muted">まだブックマークはありません。右上のしおりアイコンをタップすると保存できます。</div>
        ) : (
          <div className="hl-items">
            {bookmarks.map((b) => {
              const chapter = chapterForPara(book.body, b.paragraphIndex);
              return (
                <Link
                  key={b.id}
                  href={`/read/${book.id}?pi=${b.paragraphIndex}`}
                  className="hl-card panel"
                  style={{ borderLeftColor: "var(--text-400)" }}
                >
                  <span className="hl-kind">ブックマーク</span>
                  <span className="hl-text">{b.text}{b.text.length >= 48 ? "…" : ""}</span>
                  {chapter && <span className="hl-meta">{chapter}</span>}
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
