// 本の表紙色を「本そのもの」から決定的に導く。位置(index)やリスト順には一切依存しない
// ＝同じ本は常に同じ色。honmei は寒色（青系）、serendipity は暖色（赤系）に帯を分け、
// 安定 id のハッシュで帯の中の色を選ぶ（1冊目=青/2冊目=水色…のような決め打ちはしない）。
//
// 色被り対策: 帯ごとに「キュレート済みパレット」を持つ。各パレットは最遠点サンプリングで
// 生成し、全ペアの色差 >= ~34（隣に並べても明確に別色と読める）かつ タイトル色 #f3efe6 との
// コントラスト >= 3.0（WCAG AA 大太字）を満たす色だけで構成する。ハッシュはこの中から1色を
// 選ぶだけなので、2冊が「ほぼ同じでモヤっと」な色になる被りは構造的に生じない（起きても稀な
// 完全一致＝同色＝意図的に見える）。再生成手順は PR 参照。
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

// 各エントリは [hue(°), saturation(%), topLight(%)]（グラデ上端＝タイトル背景）。
// honmei = 寒色（ティール〜シアン〜青〜藍〜青紫, hue 170〜278）。20色・全ペア色差>=34。
const COOL_TONES: readonly (readonly [number, number, number])[] = [
  [170, 44, 22],
  [170, 73, 31],
  [178, 44, 40],
  [190, 73, 25],
  [192, 73, 40],
  [194, 73, 34],
  [206, 44, 37],
  [214, 73, 40],
  [216, 69, 34],
  [228, 49, 31],
  [232, 73, 37],
  [240, 73, 22],
  [254, 73, 31],
  [254, 73, 40],
  [256, 49, 40],
  [258, 44, 22],
  [278, 73, 40],
  [278, 64, 25],
  [278, 73, 31],
  [278, 44, 40],
];
// serendipity = 暖色（ローズ/マゼンタ〜赤〜橙〜琥珀, hue 318〜52。明るい黄は可読性のため除外）。
// 14色・全ペア色差>=38。
const WARM_TONES: readonly (readonly [number, number, number])[] = [
  [0, 83, 39],
  [0, 83, 24],
  [10, 54, 30],
  [22, 74, 36],
  [40, 83, 39],
  [44, 54, 36],
  [52, 69, 24],
  [318, 54, 24],
  [318, 83, 39],
  [318, 54, 39],
  [318, 83, 30],
  [342, 59, 39],
  [344, 83, 30],
  [346, 83, 39],
];
// グラデ下端の明度(%)。帯ごとに暗色でアンカーし、エディトリアルな締まりを保つ。
const COOL_BOTTOM = 12;
const WARM_BOTTOM = 13;

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
  const warm = isSerendipity(kind, shelf);
  const tones = warm ? WARM_TONES : COOL_TONES;
  const [hue, sat, topLight] = tones[hashId(id) % tones.length];
  const bottomLight = warm ? WARM_BOTTOM : COOL_BOTTOM;

  const top = `hsl(${hue}, ${sat}%, ${topLight}%)`;
  const bottom = `hsl(${hue}, ${sat}%, ${bottomLight}%)`;
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
