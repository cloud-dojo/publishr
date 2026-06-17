"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

// 右上の検索。Enter（送信）で /search?q=... へ遷移する。useSearchParams は使わず
// useRouter のみ＝Topbar は全ページに出るため、検索ページ以外で Suspense 境界を強制しない。
export function SearchBar() {
  const router = useRouter();
  const [q, setQ] = useState("");

  return (
    <form
      className="searchbar"
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        const term = q.trim();
        if (term) router.push(`/search?q=${encodeURIComponent(term)}`);
      }}
    >
      <span aria-hidden>⌕</span>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="作家・テーマで書庫を探す…"
        aria-label="作家・テーマで書庫を探す"
      />
    </form>
  );
}
