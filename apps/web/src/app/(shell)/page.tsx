"use client";

import { useEffect, useRef, useState } from "react";
import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID, dataSource } from "@/data/config";
import { FIRST_RUN_TOTAL } from "@/data/firstRunCatalog";
import { useProvider } from "@/data/hooks";
import {
  getFirstRunStatus,
  getInitialProfile,
  setFirstRunStatus,
  type FirstRunStatus,
} from "@/data/user-writes";
import { watchAuth } from "@/lib/firebase";
import { ARRIVAL_WINDOW_DAYS, arrivalLabel, isWithinDays } from "@/lib/arrival";

export default function HomePage() {
  const provider = useProvider();
  // ログイン中の Firebase Auth ユーザー名を優先（サイドバー・アカウントページと一致）。
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(null);
  const [uid, setUid] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => {
    setAuthDisplayName(u?.displayName ?? null);
    setUid(u?.uid ?? null);
  }), []);
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";
  // 理由は plan 由来を優先し、初回カタログ本は deliveryReason をフォールバックに。
  const reason = (b: Book) => provider.getPlan(b.planId)?.reason ?? b.deliveryReason;

  // 棚＝shelf＋直近28日ウィンドウ（ARRIVAL_WINDOW_DAYS）で導出。企画したら本文まで自動執筆＝
  // 予約導線なし。draft はすぐ published になるため status は問わず「入荷から28日以内の本」を
  // 関心(arrivals)/新しい出会い(odd)に並べる（published も消えずに残す）。
  // ※読了しても shelf は変わらない（自動で棚落ちしない）。ユーザーが「📚 書庫に保存/移動」した
  //   本だけ shelf=library になり入荷一覧から外れて書庫に残る。移動せず28日を過ぎた本は入荷から
  //   自然に落ちる（書庫には入らない・検索からは到達可）。
  const now = new Date();
  const isFreshArrival = (b: Book) => isWithinDays(b.createdAt, ARRIVAL_WINDOW_DAYS, now);
  const byNewest = (a: Book, b: Book) => (b.createdAt ?? "").localeCompare(a.createdAt ?? "");

  const interests = provider.booksByShelf("arrivals").filter(isFreshArrival).sort(byNewest);
  const encounters = provider.booksByShelf("odd").filter(isFreshArrival).sort(byNewest);
  // 執筆中（自動執筆の短時間遷移）：reserved/writing をさりげなく表示。
  const press = provider
    .listBooks()
    .filter((b) => b.status === "writing" || b.status === "reserved")
    .sort(byNewest);
  const arrival = arrivalLabel(); // 今朝 / 昨日 / おととい / 先日

  // --- 初回体験（登録直後）：空→生成中→15冊 ---
  // localStorage 読取はハイドレーション不一致を避けるためマウント後に行う。
  const [firstRun, setFirstRun] = useState<FirstRunStatus | null>(null);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFirstRun(getFirstRunStatus(uid ?? undefined));
  }, [uid]);
  const generating = firstRun === "generating";
  const freshCount = interests.length + encounters.length;
  // 完了判定：mock は全15冊そろったら、firestore は実本が1冊でも届いたら通常表示へ。
  const firstRunTarget = dataSource === "mock" ? FIRST_RUN_TOTAL : 1;

  // 生成の開始（uid ごとに1回だけ）。mockは時間差入荷、firestoreはパイプライン起動。
  // 旧実装は boolean ref で「最初の uid」が消費すると、後から確定した実 uid で発火しない/
  // 取り違える恐れがあった（#8）。uid をキーにして各ユーザーで確実に1回だけ起動する。
  const startedForRef = useRef<string | null>(null);
  useEffect(() => {
    const u = uid ?? DEMO_USER_ID;
    if (generating && startedForRef.current !== u) {
      startedForRef.current = u;
      void provider.runFirstRun(u, getInitialProfile());
    }
  }, [generating, provider, uid]);

  const finishFirstRun = () => {
    setFirstRunStatus("ready", uid ?? undefined);
    setFirstRun("ready");
  };

  // 完了したら ready にして通常表示へ。
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (generating && freshCount >= firstRunTarget) finishFirstRun();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generating, freshCount, firstRunTarget, uid]);

  // 安全装置：パイプライン未達などで本が届かなくても、一定時間で書店へ抜けられる。
  useEffect(() => {
    if (!generating) return;
    const t = setTimeout(finishFirstRun, 45_000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generating, uid]);

  if (generating) {
    const arrived = [...interests, ...encounters];
    const remaining = Math.max(0, FIRST_RUN_TOTAL - arrived.length);
    return (
      <>
        <Topbar
          greeting={
            <>
              ようこそ、<b>{authDisplayName ?? "あなた"}</b> さん。
            </>
          }
        />
        <section className="page-hero">
          <div className="ph-eyebrow">Preparing your store</div>
          <h1>
            あなたの最初の本棚を、
            <br />
            <span className="accent">仕立てています</span>。
          </h1>
        </section>
        <section className="page section">
          <div className="firstrun-note">
            <span className="fr-spinner" aria-hidden />
            <span>
              あなたの初期プロフィールと連携情報をもとに、編集部がいま書き下ろしています。
              入荷した本から順に棚へ並びます（{arrived.length} / {FIRST_RUN_TOTAL} 冊）。
            </span>
            <button type="button" className="fr-skip" onClick={finishFirstRun}>
              書店を見る →
            </button>
          </div>
          <div className="shelf-grid">
            {arrived.map((b) => (
              <BookCard
                key={b.id}
                book={b}
                authorName={authorName(b)}
                reason={reason(b)}
                showWhy
                layout="row"
              />
            ))}
            {Array.from({ length: remaining }).map((_, i) => (
              <div key={`sk-${i}`} className="book-skeleton" aria-hidden>
                <div className="bsk-cover" />
                <div className="bsk-lines">
                  <div className="bsk-line" />
                  <div className="bsk-line short" />
                  <div className="bsk-bubble" />
                </div>
              </div>
            ))}
          </div>
        </section>
      </>
    );
  }

  return (
    <>
      <Topbar
        greeting={
          <>
            おはようございます、<b>{authDisplayName ?? "ゲスト"}</b> さん。
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

    </>
  );
}
