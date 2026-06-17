"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useProvider } from "@/data/hooks";
import { watchAuth } from "@/lib/firebase";

const NAV = [
  { href: "/", ico: "❖", label: "あなたの書店" },
  { href: "/library", ico: "▤", label: "わたしの書庫" },
  { href: "/highlights", ico: "❏", label: "ハイライト・ブックマーク" },
  { href: "/authors", ico: "✒", label: "作家たち" },
  { href: "/map", ico: "✦", label: "サイトマップ" },
];

const SPINE: Record<string, string> = {
  midnight: "linear-gradient(160deg,#1b2440,#0c1226)",
  forest: "linear-gradient(160deg,#28402f,#11231a)",
  slate: "linear-gradient(160deg,#38404e,#181c25)",
  rust: "linear-gradient(160deg,#8a4326,#3d1b0f)",
};

export function Sidebar() {
  const pathname = usePathname();
  // ログイン中の Firebase Auth ユーザーを表示し、アカウントページと一致させる。
  // 未ログイン時は特定人物（デモの佐倉）を出さず「ゲスト」にする（第一印象/プライバシー）。
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => setAuthDisplayName(u?.displayName ?? null)), []);

  const readerName = authDisplayName || "ゲスト";
  const readerInitial = readerName[0] ?? "読";

  // 「最近読んだ本」＝実際に読んだ published 本（読書進捗 > 0）。shelf には依存しない
  // （企画→自動執筆した本は shelf=arrivals のままなので、旧 booksByShelf("library") では
  // 新刊が永遠に出ず「更新されない」状態だった）。新しい順に最大5冊。
  const provider = useProvider();
  const recentlyRead = provider
    .listBooks()
    .filter((b) => b.status === "published" && (b.feedback?.readPercent ?? 0) > 0)
    .sort((a, b) => (b.createdAt ?? "").localeCompare(a.createdAt ?? ""))
    .slice(0, 5);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <aside className="sidebar">
      <Link href="/" className="brand">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="brand-icon" src="/favicon.svg" alt="" width={30} height={30} aria-hidden />
        <span className="mark">
          Publishr<span className="dot">.</span>
        </span>
      </Link>
      <div className="brand-sub">あなた専属の、AI出版社。</div>

      <nav className="nav">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href} className={isActive(n.href) ? "active" : ""}>
            <span className="ico">{n.ico}</span>
            {n.label}
          </Link>
        ))}
      </nav>

      <div className="shelf-label">最近読んだ本</div>
      <div className="mini-books">
        {recentlyRead.map((b) => (
          <Link key={b.id} href={`/read/${b.id}`} className="mini-book">
            <span
              className="mini-spine"
              style={{ background: SPINE[b.coverVariant] ?? "linear-gradient(160deg,#2a2d34,#0c0d10)" }}
            />
            <span className="mini-meta">
              <span className="mini-title">{b.title}</span>
            </span>
          </Link>
        ))}
        {recentlyRead.length === 0 && (
          <div className="mini-empty">まだ読んだ本はありません</div>
        )}
      </div>

      <div className="sidebar-foot">
        <Link href="/account" className="reader-chip">
          <span className="reader-avatar">{readerInitial}</span>
          <span className="reader-name">{readerName}</span>
        </Link>
      </div>
    </aside>
  );
}
