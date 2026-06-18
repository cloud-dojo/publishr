"use client";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

export default function LibraryPage() {
  const provider = useProvider();
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";

  // 書庫＝ユーザーが「書庫へ移動」した本だけのキュレーション集（shelf==="library"）。
  // 入荷(arrivals/odd)は直近28日の新着ビュー。移動しないと28日で入荷から落ち、書庫にも入らない
  // （検索からは到達可）。新しい順。
  const library = provider
    .listBooks()
    .filter((b) => b.status === "published" && b.shelf === "library")
    .sort((a, b) => (b.createdAt ?? "").localeCompare(a.createdAt ?? ""));

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
            <BookCard key={b.id} book={b} authorName={authorName(b)} />
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
