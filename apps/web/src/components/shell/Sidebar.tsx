"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { fixtures } from "@publishr/shared-schema";

import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";
import { coverGradient } from "@/lib/coverColor";
import { watchAuth } from "@/lib/firebase";

const NAV = [
  { href: "/", ico: "❖", label: "あなたの書店" },
  { href: "/library", ico: "▤", label: "あなたの本棚" },
  { href: "/highlights", ico: "❏", label: "ハイライト・ブックマーク" },
  { href: "/authors", ico: "✒", label: "作家たち" },
  { href: "/map", ico: "✦", label: "サイトマップ" },
];

// 背表紙の既定色（本ごとの色が出せない時のフォールバック）。表紙(cover-min)と同じ暗紺。
const SPINE_FALLBACK = "linear-gradient(160deg,#232a37,#0c0e15)";

export function Sidebar() {
  const pathname = usePathname();
  const provider = useProvider();
  // ログイン中の Firebase Auth ユーザーを優先表示し、アカウントページと一致させる。
  // 未ログイン（mock 等）時はプロバイダ上のデモユーザーにフォールバック。
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(null);
  const [uid, setUid] = useState<string | null>(null);

  useEffect(() => watchAuth((u) => {
    setAuthDisplayName(u?.displayName ?? null);
    setUid(u?.uid ?? null);
  }), []);

  const fallbackUser = fixtures.users[0];
  const reader = provider.getUser(uid ?? DEMO_USER_ID) ?? fallbackUser;
  const readerName = authDisplayName?.trim() || reader?.name || "ゲスト";
  const readerInitial = readerName[0] ?? "読";

  // 「最近読んだ本」はプロバイダ経由の実データ（ログイン時は Firestore、mock 時は fixtures）。
  const library = provider
    .booksByShelf("library")
    // 書庫から外した本(dropped)は「最近読んだ本」からも消す（書庫ページと挙動を揃える）。
    .filter((b) => b.status === "published" && !b.feedback?.dropped)
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
        {library.map((b) => (
          <Link key={b.id} href={`/read/${b.id}`} className="mini-book">
            <span
              className="mini-spine"
              style={{ background: coverGradient(b.id, b.kind, b.shelf) ?? SPINE_FALLBACK }}
            />
            <span className="mini-meta">
              <span className="mini-title">{b.title}</span>
            </span>
          </Link>
        ))}
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
