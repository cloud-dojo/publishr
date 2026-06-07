"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { chapterForPara } from "@/data/bookText";
import { useProvider } from "@/data/hooks";

export default function BookHighlightsPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const book = provider.getBook(params.bookId);

  if (!book) {
    return (
      <>
        <header className="topbar">
          <div className="reader-top">
            <Link href={`/read/${params.bookId}`} className="greeting">‹ 本にもどる</Link>
          </div>
        </header>
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);
  const highlights = (book.annotations ?? [])
    .filter((a) => a.kind === "highlight")
    .slice()
    .sort((a, b) => a.paragraphIndex - b.paragraphIndex);

  return (
    <>
      <header className="topbar">
        <div className="reader-top">
          <Link href={`/read/${book.id}`} className="greeting">‹ 本にもどる</Link>
          <div className="rt-title">
            {book.title} <span>／ {persona?.name}</span>
          </div>
        </div>
      </header>

      <div className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Your highlights</div>
            <div className="section-title">
              ハイライト <span className="group-count">{highlights.length}件</span>
            </div>
            <div className="section-sub">引いた箇所をタップすると、本文の該当ページへ移動します。</div>
          </div>
        </div>

        {highlights.length === 0 ? (
          <div className="muted">まだハイライトはありません。本文をドラッグすると引けます。</div>
        ) : (
          <div className="hl-items">
            {highlights.map((h) => {
              const chapter = chapterForPara(book.body, h.paragraphIndex);
              return (
                <Link
                  key={h.id}
                  href={`/read/${book.id}?pi=${h.paragraphIndex}`}
                  className={`hl-card panel hl-card--${h.color ?? "yellow"}`}
                >
                  <span className="hl-text">
                    {h.text}{h.text.length >= 48 ? "…" : ""}
                  </span>
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
