import Link from "next/link";
import type { ReactNode } from "react";

export function Topbar({
  greeting,
  back,
  icon = "🔔",
  notify = true,
}: {
  greeting?: ReactNode;
  back?: { href: string; label: string };
  icon?: string;
  notify?: boolean;
}) {
  return (
    <header className="topbar">
      {back ? (
        <Link href={back.href} className="greeting">
          {back.label}
        </Link>
      ) : (
        <div className="greeting">{greeting}</div>
      )}
      <div className="searchbar">
        <span>⌕</span>
        <input placeholder="作家・テーマで書庫を探す…" />
      </div>
      <div className="icon-btn">
        {icon}
        {notify ? <span className="badge-dot" /> : null}
      </div>
    </header>
  );
}
