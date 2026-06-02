"use client";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

export default function LibraryPage() {
  const provider = useProvider();
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";

  const library = provider.booksByShelf("library");

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
            <BookCard key={b.id} book={b} authorName={authorName(b)} />
          ))}
          {library.length === 0 && (
            <div className="muted">{provider.ready ? "まだ蔵書がありません。" : "読み込み中…"}</div>
          )}
        </div>
      </section>
    </>
  );
}
