"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { NotificationKind } from "@publishr/shared-schema";
import { useNotifications } from "@/data/hooks";

const KIND_ICON: Record<NotificationKind, string> = {
  arrival: "📚",
  delivery: "✦",
  favoriteAuthor: "♥",
};

function relTime(iso: string): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "";
  const diff = Date.now() - t;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "たった今";
  if (min < 60) return `${min}分前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}時間前`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}日前`;
  return new Date(t).toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" });
}

export function NotificationBell() {
  const router = useRouter();
  const { notifications, unread, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // パネル外クリック / Escape で閉じる
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const onItem = (id: string, href?: string) => {
    markRead(id);
    setOpen(false);
    if (href) router.push(href);
  };

  return (
    <div className="ntf-wrap" ref={wrapRef}>
      <button
        type="button"
        className="icon-btn"
        aria-label="通知"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        🔔
        {unread > 0 && <span className="badge-count">{unread > 9 ? "9+" : unread}</span>}
      </button>

      {open && (
        <div className="ntf-panel" role="dialog" aria-label="通知一覧">
          <div className="ntf-head">
            <span className="ntf-title">通知</span>
            {unread > 0 && (
              <button type="button" className="ntf-allread" onClick={markAllRead}>
                すべて既読
              </button>
            )}
          </div>

          <div className="ntf-list">
            {notifications.length === 0 ? (
              <div className="ntf-empty">新しい通知はありません。</div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  className={`ntf-item${n.read ? "" : " unread"}`}
                  onClick={() => onItem(n.id, n.href)}
                >
                  <span className="ntf-ico">{KIND_ICON[n.kind]}</span>
                  <span className="ntf-body">
                    <span className="ntf-row1">
                      <span className="ntf-itemtitle">{n.title}</span>
                      <span className="ntf-time">{relTime(n.createdAt)}</span>
                    </span>
                    <span className="ntf-desc">{n.body}</span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
