"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { BookToc } from "@/components/book/BookToc";
import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

export default function ContentsPage() {
  const params = useParams<{ bookId: string }>();
  const provider = useProvider();
  const book = provider.getBook(params.bookId);

  if (!book) {
    return (
      <>
        <Topbar back={{ href: `/read/${params.bookId}`, label: "‹ 本にもどる" }} notify={false} icon="☰" />
        <div className="page">{provider.ready ? "本が見つかりません。" : "読み込み中…"}</div>
      </>
    );
  }

  const persona = provider.getPersona(book.authorPersonaId);

  return (
    <>
      <header className="topbar">
        <div className="reader-top">
          <Link href={`/read/${book.id}`} className="greeting">
            ‹ 本にもどる
          </Link>
          <div className="rt-title">
            {book.title} <span>／ {persona?.name}</span>
          </div>
        </div>
      </header>

      <div className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Table of contents</div>
            <div className="section-title">
              目<span className="accent">次</span>
            </div>
            <div className="section-sub">章をタップすると、その章の本文へ移動します。</div>
          </div>
        </div>

        <BookToc book={book} />
      </div>
    </>
  );
}
