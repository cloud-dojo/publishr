import type { Book } from "@publishr/shared-schema";

import { ARRIVAL_WINDOW_DAYS, isWithinDays } from "@/lib/arrival";

type BadgeSpec = { cls: string; label: string; pulse: boolean };

const READ_DONE_PERCENT = 90; // これ以上読んだら「読了」

// 予約撤去・企画→即published 後のラベル。`shelf` はライフサイクル（入荷↔書庫↔読了）でなく
// 「種別」（odd=セレンディピティ）にのみ使い、入荷/読了は recency と読書進捗で決める。
// ※ 旧実装は published を shelf で「入荷/読了」分けしていたが、shelf は published 化で
//   遷移しないため「入荷本が永遠に入荷／未読の蔵書が読了」になり矛盾していた。
function spec(book: Book): BadgeSpec | null {
  // 準備中＝自動執筆中の一時状態（draft/reserved/writing）。手動「予約」は無い。
  if (book.status !== "published") {
    return { cls: "badge--writing", label: "準備中", pulse: book.status === "writing" };
  }
  // 読了＝実際に読み終えた（shelf に依存しない）。
  if ((book.feedback?.readPercent ?? 0) >= READ_DONE_PERCENT) {
    return { cls: "badge--done", label: "読了", pulse: false };
  }
  // 入荷＝published かつ入荷から数日以内の新刊（セレンディピティは「新しい出会い」）。
  if (isWithinDays(book.createdAt, ARRIVAL_WINDOW_DAYS)) {
    return book.shelf === "odd"
      ? { cls: "badge--odd", label: "新しい出会い", pulse: false }
      : { cls: "badge--new", label: "入荷", pulse: false };
  }
  // それ以外＝蔵書（バッジ無し＝書庫のノイズを減らす）。
  return null;
}

export function StatusBadge({ book, floating = true }: { book: Book; floating?: boolean }) {
  const s = spec(book);
  if (!s) return null;
  return (
    <span className={`${floating ? "book-badge " : ""}badge ${s.cls}`}>
      {s.pulse ? <span className="pulse" /> : null}
      {s.label}
    </span>
  );
}
