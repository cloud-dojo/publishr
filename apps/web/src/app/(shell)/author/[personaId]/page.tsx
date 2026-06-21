"use client";

import { useParams } from "next/navigation";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { AUTHOR_BIOS } from "@/data/authorBios";
import { toggleFavorite, useFavorites } from "@/data/favorites-store";
import { useActions, useProvider } from "@/data/hooks";

// アイコン文字＝苗字の頭文字（name 先頭1文字）。
function monogramOf(name: string): string {
  return name.trim().charAt(0);
}

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
  const favorites = useFavorites();
  const { notifyFavoriteAuthor } = useActions();
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
  const isFav = favorites.has(persona.id);
  const bio = AUTHOR_BIOS[persona.id];
  const onToggleFav = () => {
    toggleFavorite({
      personaId: persona.id,
      name: persona.name,
      savedAt: new Date().toISOString(),
    });
    // 新規登録時のみ通知（読了画面と挙動を揃える・解除時は出さない）。
    if (!isFav) notifyFavoriteAuthor(persona.id, persona.name);
  };

  return (
    <>
      <Topbar back={{ href: "/authors", label: "← 作家たち" }} />

      <header className="author-head page">
        <span className="ah-avatar">{monogramOf(persona.name)}</span>
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
            <button
              type="button"
              className={`fav-btn ${isFav ? "on" : ""}`}
              onClick={onToggleFav}
              aria-pressed={isFav}
            >
              {isFav ? "★ お気に入り登録済み" : "☆ お気に入りの作家に登録"}
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
        {/* 背景：全幅・リード文＋箇条書き */}
        <article className="p-card panel p-card--wide">
          <span className="p-en">Background</span>
          <h3 className="p-title">背景</h3>
          {bio ? (
            <>
              <p className="p-text p-lead">{bio.lead}</p>
              <ul className="p-bullets">
                {bio.highlights.map((h) => (
                  <li key={h}>{h}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="p-text">{persona.persona.career}</p>
          )}
        </article>

        {/* 文体・専門：下に2列 */}
        <div className="persona-grid">
          <PersonaCard en="Voice" title="文体" text={persona.persona.styleNote} />
          <PersonaCard en="Expertise" title="専門・テーマ" chips={persona.expertise} />
        </div>
      </section>

      {persona.persona.thought && (
        <section className="page section">
          <div className="section-head">
            <div>
              <div className="eyebrow">Credo</div>
              <div className="section-title">
                この作家の<span className="accent">信条</span>
              </div>
            </div>
          </div>
          <blockquote className="author-quote">
            <span className="aq-mark">&ldquo;</span>
            {persona.persona.thought}
          </blockquote>
        </section>
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
