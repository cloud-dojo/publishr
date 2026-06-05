"use client";

import Link from "next/link";
import { useState } from "react";

import { Topbar } from "@/components/shell/Topbar";
import { useProvider } from "@/data/hooks";
import {
  annotationsToHighlights,
  highlightsGroupedByBook,
  highlightTagCloud,
  mergeHighlights,
  type HighlightKind,
} from "@/data/mock-highlights";

type Tab = "all" | HighlightKind;

const TABS: { key: Tab; label: string }[] = [
  { key: "all", label: "すべて" },
  { key: "highlight", label: "ハイライト" },
  { key: "note", label: "付箋" },
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

  // シード＋読書ページで付けた注釈（book.annotations）をマージ
  const items = mergeHighlights(annotationsToHighlights(provider.listBooks()));
  const count = (k: Tab) =>
    k === "all" ? items.length : items.filter((h) => h.kind === k).length;
  const groups = highlightsGroupedByBook(items, tab);
  const cloud = highlightTagCloud(items);
  const bookTitle = (id: string) => provider.getBook(id)?.title ?? id;

  return (
    <>
      <Topbar
        greeting={
          <>
            <b>ハイライトと付箋</b>　― あなたが線を引いた場所は、関心の地図になる。
          </>
        }
      />
      <section className="page-hero">
        <div className="ph-eyebrow">Your marks &amp; margins</div>
        <h1>
          ハイライトと<span className="accent">付箋</span>。
        </h1>
        <p>
          あなたが線を引いた場所・付箋を貼った場所——これはあなたの関心の地図です。次に何を書くべきかを、Publishr
          はここから学びます。
        </p>
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

        <div className="hl-layout">
          <div className="hl-list">
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
          </div>

          <aside className="hl-side">
            <div className="hl-side-card panel">
              <h3 className="hl-side-title">あなたの関心の地図</h3>
              <div className="hl-cloud">
                {cloud.map((c) => (
                  <span
                    key={c.tag}
                    className="hl-cloud-tag"
                    style={{ fontSize: 12 + Math.min(c.count, 5) * 2 }}
                  >
                    {c.tag}
                    <span className="hl-cloud-count">{c.count}</span>
                  </span>
                ))}
              </div>
            </div>
            <div className="hl-side-card panel">
              <h3 className="hl-side-title">この関心が、次の企画に</h3>
              <p className="hl-side-note">
                「{cloud[0]?.tag}」「{cloud[1]?.tag}
                」へのマーキングが多いため、来週の企画はその方向に寄せています。
              </p>
            </div>
          </aside>
        </div>
      </section>
    </>
  );
}
