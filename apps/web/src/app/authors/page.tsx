"use client";

import Link from "next/link";

import type { Persona } from "@publishr/shared-schema";

import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

function tagsOf(p: Persona): string[] {
  return [p.style, p.title].filter(Boolean);
}

function AuthorCard({ persona, bookCount }: { persona: Persona; bookCount: number }) {
  return (
    <Link href={`/author/${persona.id}`} className="author-card panel">
      <span className="ac-avatar">{persona.monogram}</span>
      <span className="ac-meta">
        <span className="ac-name">{persona.name}</span>
        <span className="ac-reading">{persona.nameReading}</span>
        <span className="ac-tags">
          {tagsOf(persona).map((t) => (
            <span key={t} className="ac-tag">
              {t}
            </span>
          ))}
        </span>
        <span className="ac-count">この書店に {bookCount}冊</span>
      </span>
    </Link>
  );
}

export default function AuthorsPage() {
  const provider = useProvider();
  const personas = provider.listPersonas();
  const books = provider.listBooks();
  const bookCount = (id: string) => books.filter((b) => b.authorPersonaId === id).length;

  const inStore = personas.filter((p) => bookCount(p.id) > 0);

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>著者の作家たち</b>　― あなたのために筆を執る、専属の書き手。
          </>
        }
      />
      <section className="page-hero">
        <div className="ph-eyebrow">Authors in your store</div>
        <h1>
          あなたの書店に並ぶ
          <br />
          <span className="accent">作家たち</span>。
        </h1>
      </section>

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Curated authors</div>
            <div className="section-title">
              企画ごとに生まれた<span className="accent">著者</span>
            </div>
            <div className="section-sub">
              Publishr が企画ごとに生み出した著者たち。読書ページや著者ページからお気に入りに登録できます。
            </div>
          </div>
        </div>
        <div className="author-grid">
          {inStore.map((p) => (
            <AuthorCard key={p.id} persona={p} bookCount={bookCount(p.id)} />
          ))}
          {inStore.length === 0 && (
            <div className="muted">{provider.ready ? "まだ作家がいません。" : "読み込み中…"}</div>
          )}
        </div>
      </section>
    </>
  );
}
