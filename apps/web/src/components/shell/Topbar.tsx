import Link from "next/link";
import type { ReactNode } from "react";

import { NotificationBell } from "./NotificationBell";

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
      {notify ? (
        <NotificationBell />
      ) : (
        <div className="icon-btn">{icon}</div>
      )}
    </header>
  );
}
