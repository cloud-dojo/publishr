"use client";

import Link from "next/link";
import type { MouseEvent } from "react";

import type { Persona } from "@publishr/shared-schema";

import { Topbar } from "@/components/shell/Topbar";
import { toggleFavorite, useFavorites } from "@/data/favorites-store";
import { useProvider } from "@/data/hooks";

// スタイル行（例：理論派 / 組織設計 / 権限委譲）。最大3語をスラッシュ区切りで。
function styleLine(p: Persona): string {
  return [p.style, ...(p.expertise ?? [])].filter(Boolean).slice(0, 3).join(" / ");
}

// アイコン文字＝苗字の頭文字（name 先頭1文字）。
function monogramOf(name: string): string {
  return name.trim().charAt(0);
}

// 信条（心情）の一言＝thought の最初の一文。どんな人かが伝わる短い惹句。
function credoOf(p: Persona): string {
  return (p.persona?.thought ?? "").split(/[。.！!？?]/)[0].trim();
}

function AuthorChip({ persona, isFav }: { persona: Persona; isFav: boolean }) {
  const onToggle = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggleFavorite({
      personaId: persona.id,
      name: persona.name,
      voiceStyle: persona.voiceStyle || persona.persona.styleNote || persona.style,
      format: persona.format || persona.title || "",
      savedAt: new Date().toISOString(),
    });
  };
  return (
    <div className="author-chip">
      <Link href={`/author/${persona.id}`} className="ach-main">
        <span className="ach-avatar">{monogramOf(persona.name)}</span>
        <span className="ach-meta">
          <span className="ach-name">{persona.name}</span>
          <span className="ach-style">{styleLine(persona)}</span>
          {credoOf(persona) && <span className="ach-credo">「{credoOf(persona)}」</span>}
        </span>
      </Link>
      <button
        type="button"
        className={`ach-fav ${isFav ? "on" : ""}`}
        onClick={onToggle}
        aria-label={isFav ? "お気に入り解除" : "お気に入りに登録"}
      >
        {isFav ? "★" : "☆"}
      </button>
    </div>
  );
}

export default function AuthorsPage() {
  const provider = useProvider();
  const favorites = useFavorites();
  const personas = provider.listPersonas();
  const books = provider.listBooks();
  const bookCount = (id: string) => books.filter((b) => b.authorPersonaId === id).length;

  const inStore = personas.filter((p) => bookCount(p.id) > 0);
  const favs = personas.filter((p) => favorites.has(p.id));

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>作家たち</b>　― あなたのために筆を執る、専属の書き手。
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

      {/* 並んでいる作家たち */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">All authors</div>
            <div className="section-title">
              現在、書店に並んでいる<span className="accent">すべて</span>の書き手
            </div>
            <div className="section-sub">
              Publishr が企画ごとに生み出した著者たち。読書ページや著者ページからお気に入りに登録できます。
            </div>
          </div>
        </div>
        <div className="author-grid">
          {inStore.map((p) => (
            <AuthorChip key={p.id} persona={p} isFav={favorites.has(p.id)} />
          ))}
          {inStore.length === 0 && (
            <div className="muted">{provider.ready ? "まだ作家がいません。" : "読み込み中…"}</div>
          )}
        </div>
      </section>

      {/* お気に入りの作家 */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Your favorite authors</div>
            <div className="section-title">
              あなたの<span className="accent">お気に入り</span>の作家
            </div>
            <div className="section-sub">
              お気に入りに登録すると、その著者がこれからもあなたのために本を書き続けます。
            </div>
          </div>
        </div>
        <div className="author-grid">
          {favs.map((p) => (
            <AuthorChip key={p.id} persona={p} isFav />
          ))}
          {favs.length === 0 && (
            <div className="muted">
              まだお気に入りの作家はいません。気に入った著者を ☆ で登録してみてください。
            </div>
          )}
        </div>
      </section>
    </>
  );
}
