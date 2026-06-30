import type { Book } from "@publishr/shared-schema";

import { ARRIVAL_WINDOW_DAYS, isWithinDays } from "@/lib/arrival";

type BadgeSpec = { cls: string; label: string; pulse: boolean };

const READ_DONE_PERCENT = 90; // これ以上読んだら「読了」

// 予約撤去・企画→即published 後のラベル。`shelf` はライフサイクル（入荷↔書庫↔読了）でなく
// 「種別」（odd=視野を広げる本）にのみ使い、入荷/読了は recency と読書進捗で決める。
// ※ 旧実装は published を shelf で「入荷/読了」分けしていたが、shelf は published 化で
//   遷移しないため「入荷本が永遠に入荷／未読の蔵書が読了」になり矛盾していた。
function spec(book: Book): BadgeSpec | null {
  // 「準備中」は廃止（全冊・配本時に本文まで生成済み＝出す前提）。draft/writing 等の一時状態でも
  // ユーザー向けには出さない＝おすすめ/読了/視野を広げる のみをバッジにする。
  // 読了＝実際に読み終えた（shelf に依存しない）。
  if ((book.feedback?.readPercent ?? 0) >= READ_DONE_PERCENT) {
    return { cls: "badge--done", label: "読了", pulse: false };
  }
  // ユーザーが書庫へ移動済み（shelf=library）は入荷扱いしない＝書庫グリッドで「入荷」と出さない。
  if (book.shelf === "library") return null;
  // published かつ一定期間内の本（odd は「視野を広げる」）。
  if (isWithinDays(book.createdAt, ARRIVAL_WINDOW_DAYS)) {
    return book.shelf === "odd"
      ? { cls: "badge--odd", label: "視野を広げる", pulse: false }
      : { cls: "badge--new", label: "おすすめ", pulse: false };
  }
  // それ以外＝蔵書（バッジ無し＝書庫のノイズを減らす）。
  return null;
}

// 書庫(library)用：入荷/種別ではなく「読書の進捗」を 未読 / 読書中 / 読了 の3状態で出す。
// readPercent: 0=未読 / 1〜89=読書中 / 90以上=読了（READ_DONE_PERCENT）。
function progressSpec(book: Book): BadgeSpec {
  const pct = book.feedback?.readPercent ?? 0;
  if (pct >= READ_DONE_PERCENT) return { cls: "badge--done", label: "読了", pulse: false };
  if (pct > 0) return { cls: "badge--reading", label: "読書中", pulse: false };
  return { cls: "badge--unread", label: "未読", pulse: false };
}

export function StatusBadge({
  book,
  floating = true,
  mode = "arrival",
}: {
  book: Book;
  floating?: boolean;
  // arrival=書店トップ（おすすめ/視野を広げる/読了）, progress=本棚（未読/読書中/読了）
  mode?: "arrival" | "progress";
}) {
  const s = mode === "progress" ? progressSpec(book) : spec(book);
  if (!s) return null;
  return (
    <span className={`${floating ? "book-badge " : ""}badge ${s.cls}`}>
      {s.pulse ? <span className="pulse" /> : null}
      {s.label}
    </span>
  );
}

