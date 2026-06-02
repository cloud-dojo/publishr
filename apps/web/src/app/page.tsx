"use client";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";

export default function HomePage() {
  const provider = useProvider();
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";
  const reason = (b: Book) => provider.getPlan(b.planId)?.reason;

  const arrivals = provider.booksByShelf("arrivals");
  const press = provider.booksByShelf("press");
  const odd = provider.booksByShelf("odd");
  const user = provider.getUser(DEMO_USER_ID);

  return (
    <>
      <Topbar
        greeting={
          <>
            おはようございます、<b>{user?.name ?? "田所 誠"}</b> さん。
            <br />
            昨夜、あなたのために <b>{arrivals.length}冊</b> の新刊が入荷しました。
          </>
        }
      />

      <section className="page-hero">
        <div className="ph-eyebrow">This morning&apos;s arrivals</div>
        <h1>
          今朝、あなたの書店に
          <br />
          <span className="accent">新しい本</span>が並びました。
        </h1>
      </section>

      {/* 今朝の入荷 */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Curated for you, autonomously</div>
            <div className="section-title">
              今朝の<span className="accent">入荷</span>
            </div>
            <div className="section-sub">
              あなたの関心と仕事の局面を読み、編集部が自律的に企画しました。
            </div>
          </div>
          <div className="right">企画：編集会議 AI ／ 装丁：Imagen</div>
        </div>
        <div className="book-grid">
          {arrivals.map((b) => (
            <BookCard key={b.id} book={b} authorName={authorName(b)} reason={reason(b)} showWhy />
          ))}
        </div>
      </section>

      {/* いま執筆中 */}
      {press.length > 0 && (
        <section className="page section">
          <div className="section-head">
            <div>
              <div className="eyebrow">In the press</div>
              <div className="section-title">
                いま、<span className="accent">執筆中</span>の本
              </div>
              <div className="section-sub">
                あなたが予約した一冊を、作家が書き継いでいます。明朝には書庫へ届きます。
              </div>
            </div>
          </div>
          <div className="rail">
            {press.map((b) => (
              <BookCard key={b.id} book={b} authorName={authorName(b)} />
            ))}
          </div>
        </section>
      )}

      {/* 今月の異色作 */}
      {odd.length > 0 && (
        <section className="page section">
          <div className="section-head">
            <div>
              <div className="eyebrow">The keeper&apos;s odd picks · 8 : 2</div>
              <div className="section-title">
                今月の<span className="accent">異色作</span>
              </div>
              <div className="section-sub">
                いつもの実務書から少し離れた棚。あえて関心の&quot;隣&quot;を混ぜています。
              </div>
            </div>
            <div className="right">店主より</div>
          </div>
          <div className="rail">
            {odd.map((b) => (
              <BookCard key={b.id} book={b} authorName={authorName(b)} />
            ))}
          </div>
        </section>
      )}

      <div className="mock-note">
        <span className="mn-ico">◈</span>
        <span>
          ローカルMVP。本・著者・入荷理由はデモ用データで、観測ソースは Google Keep（モック）です。
        </span>
      </div>
    </>
  );
}
