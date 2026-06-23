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

  const library = provider
    .listBooks()
    .filter((b) => isArchivedBook(b) && !b.feedback.dropped);

  const handleRemove = async (book: Book) => {
    if (!window.confirm(`『${book.title}』を書庫から外しますか？`)) return;
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
            <b>わたしの書庫</b>　― これまでに届いた、あなたのための本。
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
              <BookCard book={b} authorName={authorName(b)} />
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
            <div className="muted">{provider.ready ? "まだ蔵書がありません。" : "読み込み中…"}</div>
          )}
        </div>
      </section>
    </>
  );
}
