"use client";

import { useParams } from "next/navigation";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

function PersonaCard({
  en,
  title,
  text,
  chips,
}: {
  en: string;
  title: string;
  text?: string;
  chips?: string[];
}) {
  return (
    <article className="p-card panel">
      <span className="p-en">{en}</span>
      <h3 className="p-title">{title}</h3>
      {text && <p className="p-text">{text}</p>}
      {chips && (
        <div className="p-chips">
          {chips.map((c) => (
            <span key={c} className="p-chip">
              {c}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

export default function AuthorPage() {
  const params = useParams<{ personaId: string }>();
  const provider = useProvider();
  const persona = provider.getPersona(params.personaId);
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";

  if (!persona) {
    return (
      <>
        <Topbar back={{ href: "/authors", label: "← 作家たち" }} />
        <section className="page section">
          <div className="muted">
            {provider.ready ? "この著者は見つかりませんでした。" : "読み込み中…"}
          </div>
        </section>
      </>
    );
  }

  const books = provider.listBooks().filter((b) => b.authorPersonaId === persona.id);

  return (
    <>
      <Topbar back={{ href: "/authors", label: "← 作家たち" }} />

      <header className="author-head page">
        <span className="ah-avatar">{persona.monogram}</span>
        <div className="ah-meta">
          <span className="eyebrow">Your dedicated author</span>
          <h1 className="ah-name">
            {persona.name}
            <span className="ah-reading">{persona.nameReading}</span>
          </h1>
          <div className="ah-tags">
            {[persona.style, persona.title].filter(Boolean).map((t) => (
              <span key={t} className="ah-tag">
                {t}
              </span>
            ))}
          </div>
          <div className="ah-actions">
            <button type="button" className="fav-btn" title="フェーズ3でFirestore直書きに接続">
              ☆ お気に入りの作家に登録
            </button>
            <span className="ah-counts">この著者の本 {books.length}冊</span>
          </div>
        </div>
      </header>

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Introduction</div>
            <div className="section-title">
              この作家の<span className="accent">紹介</span>
            </div>
          </div>
        </div>
        <div className="persona-grid">
          <PersonaCard en="Background" title="背景" text={persona.persona.career} />
          <PersonaCard en="Voice" title="文体" text={persona.persona.styleNote} />
          <PersonaCard en="Thought" title="思想" text={persona.persona.thought} />
          <PersonaCard en="Expertise" title="専門・テーマ" chips={persona.expertise} />
        </div>
      </section>

      {persona.persona.signature[0] && (
        <blockquote className="author-quote page">
          <span className="aq-mark">&ldquo;</span>
          {persona.persona.signature.join(" ／ ")}
        </blockquote>
      )}

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Books for you</div>
            <div className="section-title">
              あなたに——<span className="accent">この著者の本</span>
            </div>
          </div>
        </div>
        {books.length > 0 ? (
          <div className="book-grid">
            {books.slice(0, 4).map((b) => (
              <BookCard key={b.id} book={b} authorName={authorName(b)} />
            ))}
          </div>
        ) : (
          <div className="muted">この著者の本は、まだあなたの棚にありません。</div>
        )}
      </section>
    </>
  );
}
