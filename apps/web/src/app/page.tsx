"use client";

import type { Book } from "@publishr/shared-schema";

import { BookCard } from "@/components/book/BookCard";
import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID } from "@/data/config";
import { usePlanningCandidates, useProvider } from "@/data/hooks";
import { arrivalLabel } from "@/lib/arrival";

export default function HomePage() {
  const provider = useProvider();
  const { approvedPlanIds } = usePlanningCandidates();
  const authorName = (b: Book) => provider.getPersona(b.authorPersonaId)?.name ?? "";
  const reason = (b: Book) => provider.getPlan(b.planId)?.reason;

  const approvedPlanSet = new Set(approvedPlanIds);
  // shelf 対応: arrivals=関心 / odd=新しい出会い / press=執筆中
  const interestsBase = provider
    .booksByShelf("arrivals")
    .filter((b) => approvedPlanSet.size === 0 || approvedPlanSet.has(b.planId));
  // TODO(暫定): レイアウト確認用に同じ本を繰り返して4冊に水増し。データ確定後 interestsBase に戻す。
  const interests =
    interestsBase.length > 0
      ? Array.from({ length: 4 }, (_, i) => interestsBase[i % interestsBase.length])
      : interestsBase;
  const encounters = provider.booksByShelf("odd");
  const press = provider.booksByShelf("press");
  const user = provider.getUser(DEMO_USER_ID);
  const arrival = arrivalLabel(); // 今朝 / 昨日 / おととい / 先日

  return (
    <>
      <Topbar
        greeting={
          <>
            おはようございます、<b>{user?.name ?? "田所 誠"}</b> さん。
            <br />
            {arrival}、あなたのために <b>{interests.length}冊</b> の新刊が入荷しました。
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
              あなたの状況を観測し、専属の編集部が選び、書き下ろした一冊たちです。
            </div>
          </div>
        </div>

        {/* グループ：いま、あなたの関心に */}
        <div className="group-head">
          <div className="group-title">
            いま、あなたの関心に <span className="group-count">{interests.length}冊</span>
          </div>
          <div className="group-note">観測したいまの状況に、まっすぐ応える本。</div>
        </div>
        <div className="shelf-grid">
          {interests.map((b, i) => (
            <BookCard
              key={`${b.id}-${i}`}
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
          ローカルMVP。本・著者・入荷理由はデモ用データで、観測ソースは Google Keep（モック）です。
        </span>
      </div>
    </>
  );
}
