import type { ReactNode } from "react";

import { BackLink } from "./NavigationHistory";
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
        <BackLink href={back.href} className="greeting">
          {back.label}
        </BackLink>
      ) : (
        <div className="greeting">{greeting}</div>
      )}
      <div className="searchbar">
        <span>⌕</span>
        <input placeholder="作家・テーマで本を探す…" />
      </div>
      {notify ? (
        <NotificationBell />
      ) : (
        <div className="icon-btn">{icon}</div>
      )}
    </header>
  );
}
