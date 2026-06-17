"use client";

import Link from "next/link";

import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";

const FLOW = [
  { en: "Sense", ja: "読み取り", desc: "Drive・Calendar・Tasks を週1回読み取る" },
  { en: "Deliberate", ja: "企画判断", desc: "3階層エージェント会議 → スコアゲート" },
  { en: "Publish", ja: "出版", desc: "著者を選び、本文を書き下ろす" },
  { en: "Learn", ja: "学習", desc: "ハイライト・FB・お気に入りが次へ反映" },
];

// book: 実在の本に依存するリンク（ハードコードIDだと本が無いと404になるため動的解決する）。
type Card = {
  group: string;
  to?: string;
  book?: "detail" | "reading";
  icon: string;
  title: string;
  desc: string;
};

const CARDS: Card[] = [
  { group: "はじめる", to: "/onboarding", icon: "📝", title: "初回登録", desc: "業界・職種・関心をタップで登録（5問）。" },
  { group: "はじめる", to: "/connect",    icon: "🔗", title: "データ連携", desc: "Drive・Calendar・Tasks の読み取りに同意。" },
  { group: "届く", to: "/", icon: "▣", title: "書店トップ", desc: "今朝の入荷。なぜこの本かを添えて並ぶ。" },
  { group: "選ぶ・作る", book: "detail", icon: "📖", title: "本の詳細", desc: "企画情報・序文・著者・目次を確認する。" },
  { group: "読む・育つ", book: "reading", icon: "📚", title: "読書", desc: "本文・ハイライト・ブックマーク・★評価。" },
  { group: "読む・育つ", to: "/library", icon: "▤", title: "わたしの書庫", desc: "読了・統計を横断。棚が育つ。" },
  { group: "読む・育つ", to: "/highlights", icon: "❏", title: "ハイライト・ブックマーク", desc: "線を引いた場所＝関心の地図。" },
  { group: "読む・育つ", to: "/authors", icon: "✒", title: "作家たち", desc: "作家の紹介・名言・お気に入り登録。" },
];

export default function MapPage() {
  const provider = useProvider();
  const groups = [...new Set(CARDS.map((c) => c.group))];
  // 例示リンクは実在の published 本へ。無ければ書庫へフォールバック（ハードコードIDの404を回避）。
  const sampleId = provider.listBooks().find((b) => b.status === "published")?.id;
  const hrefOf = (c: Card): string | undefined => {
    if (c.to) return c.to;
    if (!c.book) return undefined;
    if (!sampleId) return "/library";
    return c.book === "detail" ? `/books/${sampleId}` : `/read/${sampleId}`;
  };

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>体験の地図</b>　― すべての画面は、ひとつの記憶ループにある。
          </>
        }
      />
      <section className="page-hero">
        <div className="ph-eyebrow">The map of the experience</div>
        <h1>
          Publishr 体験の<span className="accent">地図</span>。
        </h1>
        <p>すべての画面は、ひとつの記憶ループにあります。各画面が翌週の企画を更新します。</p>
      </section>

      <section className="page section">
        <div className="map-flow">
          {FLOW.map((f, i) => (
            <div key={f.en} className="map-flow-item">
              <span className="mf-en">{f.en}</span>
              <span className="mf-ja">{f.ja}</span>
              <span className="mf-desc">{f.desc}</span>
              {i < FLOW.length - 1 && <span className="mf-arrow">→</span>}
            </div>
          ))}
        </div>

        {groups.map((g) => (
          <div key={g} className="map-section">
            <div className="map-group-label">{g}</div>
            <div className="map-cards">
              {CARDS.filter((c) => c.group === g).map((c) => {
                const href = hrefOf(c);
                return href ? (
                  <Link key={c.title} href={href} className="map-card panel">
                    <span className="mc-icon">{c.icon}</span>
                    <span className="mc-title">{c.title}</span>
                    <span className="mc-desc">{c.desc}</span>
                    <span className="mc-go">開く →</span>
                  </Link>
                ) : (
                  <div key={c.title} className="map-card panel disabled">
                    <span className="mc-icon">{c.icon}</span>
                    <span className="mc-title">{c.title}</span>
                    <span className="mc-desc">{c.desc}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </section>
    </>
  );
}
