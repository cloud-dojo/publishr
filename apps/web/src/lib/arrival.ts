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

/** 入荷棚の保持期間（日）。これより古い本は入荷一覧から自動で落ちる（書庫には残る）。
 *  4週間＝4冊/日×週3回 で自然に最大 ~48冊のストック型運用。 */
export const ARRIVAL_WINDOW_DAYS = 28;

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

/** hero 用：**実際に並んでいる最新入荷(createdAt)** から粗いラベルを出す。今朝/昨日/おととい/先日。
 *  入荷スケジュールの仮定（latestArrivalDate）に依存せず実データに合わせるため、本が無い場合は ""。 */
export function arrivalHeroLabel(createdAt: string | undefined, now: Date = new Date()): string {
  if (!createdAt) return "";
  const t = new Date(createdAt);
  if (Number.isNaN(t.getTime())) return "";
  const startToday = new Date(now);
  startToday.setHours(0, 0, 0, 0);
  const startThat = new Date(t);
  startThat.setHours(0, 0, 0, 0);
  const days = Math.round((startToday.getTime() - startThat.getTime()) / 86_400_000);
  if (days <= 0) return "今朝";
  if (days === 1) return "昨日";
  if (days === 2) return "おととい";
  return "先日";
}

/** 各本の入荷日(createdAt)を相対表記で。今朝 / 昨日 / おととい / N日前（〜6日）/ M/D（1週間以上前）。
 *  4週間保持の入荷一覧で「いつ入荷したか」を本ごとに示すために使う。 */
export function arrivedLabel(createdAt: string | undefined, now: Date = new Date()): string {
  if (!createdAt) return "";
  const t = new Date(createdAt);
  if (Number.isNaN(t.getTime())) return "";
  const startToday = new Date(now);
  startToday.setHours(0, 0, 0, 0);
  const startThat = new Date(t);
  startThat.setHours(0, 0, 0, 0);
  const days = Math.round((startToday.getTime() - startThat.getTime()) / 86_400_000);
  if (days <= 0) return "今朝";
  if (days === 1) return "昨日";
  if (days === 2) return "おととい";
  if (days <= 6) return `${days}日前`;
  return `${t.getMonth() + 1}/${t.getDate()}`;
}
