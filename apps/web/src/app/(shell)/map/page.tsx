"use client";

import Link from "next/link";

import { Topbar } from "@/components/shell/Topbar";

const FLOW = [
  { en: "Start", ja: "始める", desc: "仕事や関心の土台を登録する" },
  { en: "Plan", ja: "企画される", desc: "メモや読書履歴から本の企画が生まれる" },
  { en: "Arrive", ja: "届く", desc: "あなたの書店に本が並ぶ" },
  { en: "Read", ja: "読む", desc: "本文を読み、線を引き、反応を残す" },
  { en: "Grow", ja: "育つ", desc: "本棚や感想が次の企画に活きる" },
];

type Card = { group: string; to?: string; icon: string; title: string; desc: string };

const CARDS: Card[] = [
  { group: "始める", to: "/onboarding", icon: "🚀", title: "初期設定", desc: "職種や関心を登録し、書店の土台をつくる。" },
  { group: "始める", to: "/connect", icon: "💻", title: "データ連携", desc: "Drive・Calendar・Tasks の読み取りに同意する。" },
  { group: "企画される", icon: "💡", title: "本の企画", desc: "メモや読書履歴から、必要そうな本が自動で企画される。" },
  { group: "届く", to: "/", icon: "🏬", title: "あなたの書店", desc: "届いた本が並び、なぜこの本かを確認できる。" },
  { group: "届く", to: "/books/b_makasekata", icon: "📖", title: "本の詳細", desc: "目次、序文、作家、読む理由を見てから開く。" },
  { group: "読む", to: "/read/b_100nichi", icon: "👓", title: "読書", desc: "本文を読み、ハイライトやブックマークを残す。" },
  { group: "読む", to: "/highlights", icon: "🖍️", title: "ハイライト・ブックマーク", desc: "線を引いた場所や残した印をまとめて見返す。" },
  { group: "残す・育つ", to: "/library", icon: "📚", title: "あなたの本棚", desc: "残しておきたい本を集め、あとから開ける場所。" },
  { group: "残す・育つ", to: "/authors", icon: "✍️", title: "作家たち", desc: "作家の紹介や名言を見て、お気に入りに登録する。" },
  { group: "残す・育つ", to: "/account", icon: "👤", title: "アカウント", desc: "プロフィールや読書の傾向を確認する。" },
];

export default function MapPage() {
  const groups = [...new Set(CARDS.map((c) => c.group))];
  const groupSteps = new Map(groups.map((g, i) => [g, i + 1]));

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>サイトマップ</b>　― Publishr の画面と流れを一覧できます。
          </>
        }
      />
      <div className="scaled-page">
        <section className="page-hero">
          <div className="ph-eyebrow">The map of the experience</div>
          <h1>
            Publishr 体験の<span className="accent">地図</span>。
          </h1>
        </section>

        <section className="page section">
          <div className="map-flow">
            {FLOW.map((f, i) => (
              <div key={f.en} className="map-flow-item">
                <span className="mf-step">Step {i + 1}</span>
                <span className="mf-en">{f.en}</span>
                <span className="mf-ja">{f.ja}</span>
                <span className="mf-desc">{f.desc}</span>
                {i < FLOW.length - 1 && <span className="mf-arrow">→</span>}
              </div>
            ))}
          </div>

          <div className="map-detail-head">
            <span className="mdh-rule" />
            <span className="mdh-label">各ステップの詳細</span>
            <span className="mdh-rule" />
          </div>

          {groups.map((g) => (
            <div key={g} className="map-section">
              <div className="map-group-label">
                <span className="mgl-step">{String(groupSteps.get(g)).padStart(2, "0")}</span>
                <span>{g}</span>
              </div>
              <div className="map-cards">
                {CARDS.filter((c) => c.group === g).map((c) =>
                  c.to ? (
                    <Link key={c.title} href={c.to} className="map-card panel">
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
                  )
                )}
              </div>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
