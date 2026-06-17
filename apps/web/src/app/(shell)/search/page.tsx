"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

function SearchResults() {
  const provider = useProvider();
  const params = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const ql = q.toLowerCase();

  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";
  // 作家・テーマ・タイトル等を横断して部分一致（書庫＝published 本が対象）。
  const haystack = (b: Book) =>
    [b.title, b.subtitle, authorName(b), b.deliveryReason, b.problemToSolve, b.coreMessage]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

  const results = q
    ? provider
        .listBooks()
        .filter((b) => b.status === "published" && haystack(b).includes(ql))
        .sort((a, b) => (b.createdAt ?? "").localeCompare(a.createdAt ?? ""))
    : [];

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>検索</b>　― 作家・テーマで書庫を探す。
          </>
        }
      />
      <section className="page-hero">
        <div className="ph-eyebrow">Search</div>
        <h1>
          {q ? (
            <>
              「<span className="accent">{q}</span>」の検索結果
            </>
          ) : (
            <>本を探す</>
          )}
        </h1>
        {q ? <p className="muted">{results.length} 件</p> : null}
      </section>

      <section className="page section">
        <div className="book-grid">
          {results.map((b) => (
            <BookCard key={b.id} book={b} authorName={authorName(b)} />
          ))}
          {q && results.length === 0 && (
            <div className="muted">
              {provider.ready ? "該当する本がありません。" : "読み込み中…"}
            </div>
          )}
          {!q && <div className="muted">上の検索窓に作家名やテーマを入力してください。</div>}
        </div>
      </section>
    </>
  );
}

export default function SearchPage() {
  // useSearchParams は Suspense 境界が必要（静的生成のCSRバウンド回避）。
  return (
    <Suspense fallback={<div className="page section muted">読み込み中…</div>}>
      <SearchResults />
    </Suspense>
  );
}
