import Link from "next/link";
import type { ReactNode } from "react";

import { NotificationBell } from "./NotificationBell";
import { SearchBar } from "./SearchBar";

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
      <SearchBar />
      {notify ? (
        <NotificationBell />
      ) : (
        <div className="icon-btn">{icon}</div>
      )}
    </header>
  );
}
