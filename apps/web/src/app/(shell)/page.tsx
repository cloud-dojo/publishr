"use client";

import { useEffect, useState } from "react";
import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";
import { watchAuth } from "@/lib/firebase";
import { ARRIVAL_WINDOW_DAYS, arrivalLabel, isWithinDays } from "@/lib/arrival";

export default function HomePage() {
  const provider = useProvider();
  // ログイン中の Firebase Auth ユーザー名を優先（サイドバー・アカウントページと一致）。
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => setAuthDisplayName(u?.displayName ?? null)), []);
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";
  const reason = (b: Book) => provider.getPlan(b.planId)?.reason;

  // 棚＝status＋shelf(=themeKind相当)＋直近7日ウィンドウで導出（mvp-scope §5-2）。
  // - 関心/新しい出会い：status=draft かつ 入荷から7日以内（予約すると status が変わり自動で棚落ち）
  // - 執筆中：status=reserved/writing（予約された本がここへ移る）
  const now = new Date();
  const isFreshDraft = (b: Book) =>
    b.status === "draft" && isWithinDays(b.createdAt, ARRIVAL_WINDOW_DAYS, now);
  const byNewest = (a: Book, b: Book) => (b.createdAt ?? "").localeCompare(a.createdAt ?? "");

  const interests = provider.booksByShelf("arrivals").filter(isFreshDraft).sort(byNewest);
  const encounters = provider.booksByShelf("odd").filter(isFreshDraft).sort(byNewest);
  const press = provider
    .listBooks()
    .filter((b) => b.status === "writing" || b.status === "reserved")
    .sort(byNewest);
  const user = provider.getUser(DEMO_USER_ID);
  const arrival = arrivalLabel(); // 今朝 / 昨日 / おととい / 先日

  return (
    <>
      <Topbar
        greeting={
          <>
            おはようございます、<b>{authDisplayName ?? user?.name ?? "佐倉 美咲"}</b> さん。
          </>
        }
      />

      <section className="page-hero">
        <div className="ph-eyebrow">This morning&apos;s arrivals</div>
        <h1>
          {arrival}、あなたの書店に
          <br />
          <span className="accent">新しい本</span>が並びました。
        </h1>
      </section>

      {/* 今週の入荷（関心 → 新しい出会い） */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Curated for you this week</div>
            <div className="section-title">
              今週の<span className="accent">入荷</span>
            </div>
            <div className="section-sub">
              あなたの仕事と関心を読み取り、専属の編集部が選び、書き下ろした一冊たちです。
            </div>
          </div>
        </div>

        {/* グループ：いま、あなたの関心に */}
        <div className="group-head">
          <div className="group-title">
            いま、あなたの関心に <span className="group-count">{interests.length}冊</span>
          </div>
          <div className="group-note">あなたのいまに、まっすぐ応える本。</div>
        </div>
        <div className="shelf-grid">
          {interests.map((b) => (
            <BookCard
              key={b.id}
              book={b}
              authorName={authorName(b)}
              reason={reason(b)}
              showWhy
              layout="row"
            />
          ))}
        </div>

        {/* グループ：新しい出会い */}
        {encounters.length > 0 && (
          <>
            <div className="group-head group-head--spaced">
              <div className="group-title">
                新しい出会い <span className="group-count">{encounters.length}冊</span>
              </div>
              <div className="group-note">関心の少し外側から、視野を広げる本。</div>
            </div>
            <div className="shelf-grid">
              {encounters.map((b) => (
                <BookCard
                  key={b.id}
                  book={b}
                  authorName={authorName(b)}
                  reason={reason(b)}
                  showWhy
                  layout="row"
                />
              ))}
            </div>
          </>
        )}
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
          <div className="shelf-grid">
            {press.map((b) => (
              <BookCard key={b.id} book={b} authorName={authorName(b)} layout="row" />
            ))}
          </div>
        </section>
      )}

      <div className="mock-note">
        <span className="mn-ico">◈</span>
        <span>
          ローカルMVP。本・著者・入荷理由はデモ用データで、情報ソースは Google Keep（モック）です。
        </span>
      </div>
    </>
  );
}
