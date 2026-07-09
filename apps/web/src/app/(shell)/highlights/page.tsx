"use client";

import Link from "next/link";
import { useState } from "react";

import { Topbar } from "@/components/shell/Topbar";
import { dataSource } from "@/data/config";
import { useProvider } from "@/data/hooks";
import {
  annotationsToHighlights,
  highlightsGroupedByBook,
  mergeHighlights,
  type HighlightKind,
} from "@/data/mock-highlights";

type Tab = "all" | HighlightKind;

const TABS: { key: Tab; label: string }[] = [
  { key: "all", label: "すべて" },
  { key: "highlight", label: "ハイライト" },
  { key: "bookmark", label: "ブックマーク" },
];

const KIND_LABEL: Record<HighlightKind, string> = {
  highlight: "ハイライト",
  note: "付箋",
  bookmark: "ブックマーク",
};

export default function HighlightsPage() {
  const provider = useProvider();
  const [tab, setTab] = useState<Tab>("all");

  // 読書ページで付けた注釈（book.annotations）。シードmockは mock デモ時のみ混ぜる。
  // firestore/bff（本番・実ユーザー）では、本がゼロなら何も出さない（実データのみ）。
  const items = mergeHighlights(annotationsToHighlights(provider.listBooks()), dataSource === "mock");
  // 書庫から外した本（feedback.dropped）のハイライト/ブックマークは消す＝書庫から外す＝
  // その本に紐づく痕跡もすべて消える、という正しい挙動（library の確認文言と一致させる）。
  const droppedIds = new Set(
    provider.listBooks().filter((b) => b.feedback?.dropped).map((b) => b.id)
  );
  const visibleItems = items.filter((h) => h.kind !== "note" && !droppedIds.has(h.bookId));
  const count = (k: Tab) =>
    k === "all" ? visibleItems.length : visibleItems.filter((h) => h.kind === k).length;
  const groups = highlightsGroupedByBook(visibleItems, tab);
  const bookTitle = (id: string) => provider.getBook(id)?.title ?? id;

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>ハイライトとブックマーク</b>　― あなたが線を引いた場所は、関心の地図になる。
          </>
        }
      />
      <div className="scaled-page">
      <section className="page-hero">
        <div className="ph-eyebrow">Your marks &amp; margins</div>
        <h1>
          ハイライトと<span className="accent">ブックマーク</span>。
        </h1>
      </section>

      <section className="page section">
        <div className="segment" style={{ marginBottom: 24 }}>
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              className={tab === t.key ? "on" : ""}
              onClick={() => setTab(t.key)}
            >
              {t.label} {count(t.key)}
            </button>
          ))}
        </div>

        {/* TODO(フェーズ3): ハイライトを読者分析AIのインプットとして使う。
            - observe ステップで直近1ヶ月のハイライトを取得し、Drive/Gmail/Calendar と合わせてLLMへ渡す
            - データはFirestore users/{uid}/highlights に保存し、createdAt DESC でフィルタ */}
        {groups.map((g) => (
          <section key={g.bookId} className="hl-group">
            <Link href={`/books/${g.bookId}`} className="hl-group-head">
              <span className="hl-group-title">{bookTitle(g.bookId)}</span>
              <span className="hl-group-count">{g.items.length}件</span>
            </Link>
            <div className="hl-items">
              {g.items.map((h) => (
                <Link
                  key={h.id}
                  href={`/read/${h.bookId}`}
                  className={`hl-card panel ${h.kind === "note" ? "note" : ""}`}
                >
                  <span className="hl-kind">{KIND_LABEL[h.kind]}</span>
                  <span className="hl-text">{h.text}</span>
                  {h.note && <span className="hl-note">📝 {h.note}</span>}
                  <span className="hl-meta">
                    {h.chapter}
                    {h.tags.length > 0 && <span className="hl-tags"> ・ {h.tags.join(" / ")}</span>}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        ))}
        {groups.length === 0 && <div className="muted">該当するハイライトはありません。</div>}
      </section>
      </div>
    </>
  );
}
