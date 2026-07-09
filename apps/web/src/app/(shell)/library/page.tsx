"use client";

import { useState } from "react";
import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { useActions, useProvider } from "@/data/hooks";
import { isArchivedBook } from "@/lib/arrival";

export default function LibraryPage() {
  const provider = useProvider();
  const { removeFromLibrary } = useActions();
  const [removingId, setRemovingId] = useState<string | null>(null);
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";

  // 書庫＝ユーザーが「書庫へ移動」した本だけのキュレーション集。入荷(arrivals/odd)は直近30日の
  // 新着ビューで、移動しないと30日で入荷から落ち書庫にも入らない（検索からは到達可）。新しい順。
  // 判定は archivedAt セット or shelf=library（saveToLibrary は archivedAt のみ更新するため生 shelf
  // ではなく isArchivedBook で見る・I-30）。書庫から外した本（feedback.dropped）は除外。
  // ※ status は問わない：本命/セレンディピティを含む書店の本は mock だと draft のことがあり、
  //   以前 status==="published" を要求していたため保存しても本棚に出なかった。ユーザーが明示的に
  //   保存(archivedAt)した本は draft でも「あなたの本棚」に並べる（保存意思を尊重する）。
  const library = provider
    .listBooks()
    .filter((b) => isArchivedBook(b) && !b.feedback?.dropped)
    .sort((a, b) => (b.createdAt ?? "").localeCompare(a.createdAt ?? ""));
  const handleRemove = async (book: Book) => {
    if (
      !window.confirm(
        `『${book.title}』を本棚から外しますか？\n\n` +
          `外すと本棚から消えます。引いたハイライト・付けたブックマークも一緒に消え、` +
          `元に戻すことはできません。`
      )
    )
      return;
    setRemovingId(book.id);
    try {
      await removeFromLibrary(book.id);
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>あなたの本棚</b>　― 残しておきたい、お気に入りの本。
          </>
        }
      />
      <div className="scaled-page library-page">
        <section className="page-hero">
          <div className="ph-eyebrow">Your bookshelf</div>
          <h1>
            あなただけの本が、<br />
            <span className="accent">ここに並びます</span>。
          </h1>
        </section>

        <section className="page section">
          <div className="book-grid">
            {library.map((b) => (
              <div key={b.id} className="library-book">
                <BookCard book={b} authorName={authorName(b)} showArrived={false} badgeMode="progress" />
                <button
                  type="button"
                  className="library-remove"
                  disabled={removingId === b.id}
                  onClick={() => void handleRemove(b)}
                >
                  {removingId === b.id ? "外しています..." : "本棚から外す"}
                </button>
              </div>
            ))}
            {library.length === 0 && (
              <div className="muted">
                {provider.ready
                  ? "まだ本棚に本がありません。気に入った本を「本棚に保存」すると、ここに集まります。"
                  : "読み込み中…"}
              </div>
            )}
            </div>
        </section>
      </div>
    </>
  );
}
