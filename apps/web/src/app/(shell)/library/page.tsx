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

  // 書庫＝ユーザーが「書庫へ移動」した本だけのキュレーション集（shelf==="library"）。
  // 入荷(arrivals/odd)は直近28日の新着ビュー。移動しないと28日で入荷から落ち、書庫にも入らない
  // （検索からは到達可）。新しい順。
  // 書庫＝「書庫へ移動」した本（archivedAt セット or shelf=library）。saveToLibrary は archivedAt のみ
  // 更新するため生 shelf ではなく isArchivedBook で判定する（I-30）。書庫から外した本（feedback.dropped）
  // は除外。新しい順。
  const library = provider
    .listBooks()
    .filter((b) => b.status === "published" && isArchivedBook(b) && !b.feedback?.dropped)
    .sort((a, b) => (b.createdAt ?? "").localeCompare(a.createdAt ?? ""));
  const handleRemove = async (book: Book) => {
    if (
      !window.confirm(
        `『${book.title}』を書庫から外しますか？\n\n` +
          `外すと、この本はもう読めなくなります。引いたハイライト・付けたブックマークもすべて消え、` +
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
            <b>わたしの書庫</b>　― あなたが書庫に集めた、お気に入りの蔵書。
          </>
        }
      />
      <section className="page-hero">
        <div className="ph-eyebrow">Your library</div>
        <h1>
          あなたのために書かれた<br />
          <span className="accent">蔵書</span>。
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
                {removingId === b.id ? "外しています..." : "書庫から外す"}
              </button>
            </div>
          ))}
          {library.length === 0 && (
            <div className="muted">
              {provider.ready
                ? "まだ蔵書がありません。入荷で気に入った本を「📚 書庫へ移動」すると、ここに集まります。"
                : "読み込み中…"}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
