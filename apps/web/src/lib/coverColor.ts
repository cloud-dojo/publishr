// 本の表紙色を「本そのもの」から決定的に導く。位置(index)やリスト順には一切依存しない
// ＝同じ本は常に同じ色。honmei は寒色（青系）、serendipity は暖色（赤系）に帯を分け、
// 安定 id のハッシュで帯の中の色相をばらけさせる（1冊目=青/2冊目=水色…のような決め打ちはしない）。
//
// 色は CSS カスタムプロパティ --cover-bg として渡し、globals.css の .cover-min が
// background: var(--cover-bg, <既定暗色>) で参照する。id が無い等で色を出せない時は
// 既定の暗色グラデにフォールバックする。

// FNV-1a 32bit。決定的・高分散で、Math.random/日時に依存しない（SSR/CSRで一致する）。
function hashId(input: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

type Band = {
  // 色相の開始と幅（度）。warm は 346→52 のように 360 をまたぐため mod 360 で丸める。
  hueStart: number;
  hueSpan: number;
  satBase: number; // 彩度の下限(%)
  topLightBase: number; // グラデ上端の明度下限(%)
  bottomLight: number; // グラデ下端の明度(%)
};

// honmei = 青系（シアン寄り〜藍まで）で「青の本」に見える帯に寄せる。
const COOL: Band = { hueStart: 200, hueSpan: 58, satBase: 46, topLightBase: 27, bottomLight: 13 };
// serendipity = 暖色（ワイン/赤〜橙〜琥珀）。暗くしても赤系に見えるよう彩度と明度をやや高めに。
const WARM: Band = { hueStart: 346, hueSpan: 66, satBase: 56, topLightBase: 30, bottomLight: 14 };

// セレンディピティ（＝暖色）判定。kind が "serendipity" のとき、または書店の
// 「視野を広げる本」棚(shelf==="odd")のとき暖色にする。fixtures/一部データは
// kind を "honmei" のままにして odd 棚だけで出会い枠を表すため、shelf も併用する。
function isSerendipity(kind?: string | null, shelf?: string | null): boolean {
  return (kind ?? "").toLowerCase() === "serendipity" || (shelf ?? "") === "odd";
}

/** 本(id + kind + shelf)から決定的に表紙グラデーションを返す。id が空なら null（＝既定暗色にフォールバック）。 */
export function coverGradient(
  id: string,
  kind?: string | null,
  shelf?: string | null,
): string | null {
  if (!id) return null;
  const band = isSerendipity(kind, shelf) ? WARM : COOL;
  const h = hashId(id);
  const t = (h % 10000) / 10000; // 0..1: 帯の中の色相位置
  const satJitter = (h >>> 13) % 10; // 0..9: 本ごとの彩度ゆらぎ
  const lightJitter = (h >>> 19) % 8; // 0..7: 本ごとの明度ゆらぎ

  const hue = Math.round((band.hueStart + t * band.hueSpan) % 360);
  const sat = band.satBase + satJitter;
  const topLight = band.topLightBase + lightJitter;

  const top = `hsl(${hue}, ${sat}%, ${topLight}%)`;
  const bottom = `hsl(${hue}, ${sat}%, ${band.bottomLight}%)`;
  return `linear-gradient(160deg, ${top}, ${bottom})`;
}

/** インライン style に展開できる CSS 変数の形で返す。色が無い時は空オブジェクト（CSS 側の既定に任せる）。 */
export function coverColorVars(
  id: string,
  kind?: string | null,
  shelf?: string | null,
): Record<string, string> {
  const gradient = coverGradient(id, kind, shelf);
  return gradient ? { "--cover-bg": gradient } : {};
}
