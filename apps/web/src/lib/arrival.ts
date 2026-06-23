// 入荷タイミングの相対表現（今朝／昨日／おととい／先日）。
// 企画バッチは 水・土・日 の朝7時に走る前提（docs: Cloud Scheduler 週3回）。
// 直近の「過去の入荷時刻」を求め、今日からの日数差で言葉を選ぶ。
// ※ 本番では books の arrivedAt 等のタイムスタンプができたら、それを基準に差し替える。

const ARRIVAL_DAYS = [0, 3, 6]; // 日(0) / 水(3) / 土(6)
const ARRIVAL_HOUR = 7; // 朝7時

/** now 以前で最も近い「入荷日(水/土/日) の 07:00」を返す。 */
export function latestArrivalDate(now: Date = new Date()): Date {
  const base = new Date(now);
  base.setHours(ARRIVAL_HOUR, 0, 0, 0);
  for (let i = 0; i < 8; i++) {
    const cand = new Date(base);
    cand.setDate(base.getDate() - i);
    if (ARRIVAL_DAYS.includes(cand.getDay()) && cand.getTime() <= now.getTime()) {
      return cand;
    }
  }
  return base;
}

/** "今週の入荷"棚の保持期間（日）。これより古い未保存（書庫へ移していない）本は棚落ち。
 *  予約制廃止改定 2026-06-23: 28日化は撤回し7日を維持。書庫へ移した本だけ永久保存。 */
export const ARRIVAL_WINDOW_DAYS = 30;

export interface ArrivalBookLike {
  createdAt?: string;
  archivedAt?: string | null;
  shelf?: string;
}

/** createdAt(ISO) が now から指定日数以内か。未設定(undefined)は true（棚から消さない）。 */
export function isWithinDays(
  createdAt: string | undefined,
  days: number,
  now: Date = new Date()
): boolean {
  if (!createdAt) return true;
  const t = new Date(createdAt).getTime();
  if (Number.isNaN(t)) return true;
  return now.getTime() - t <= days * 86_400_000;
}

export function isArchivedBook(book: ArrivalBookLike): boolean {
  return Boolean(book.archivedAt) || book.shelf === "library";
}

export function isVisibleArrival(
  book: ArrivalBookLike,
  days: number = ARRIVAL_WINDOW_DAYS,
  now: Date = new Date()
): boolean {
  return !isArchivedBook(book) && isWithinDays(book.createdAt, days, now);
}

/** 直近入荷からの相対表現。今朝 / 昨日 / おととい / 先日。 */
export function arrivalLabel(now: Date = new Date()): string {
  const arrived = latestArrivalDate(now);
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);
  const startOfArrived = new Date(arrived);
  startOfArrived.setHours(0, 0, 0, 0);
  const days = Math.round(
    (startOfToday.getTime() - startOfArrived.getTime()) / 86_400_000
  );
  if (days <= 0) return "今朝";
  if (days === 1) return "昨日";
  if (days === 2) return "おととい";
  return "先日";
}
