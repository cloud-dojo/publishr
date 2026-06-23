// 初回体験用の本カタログ（決定的）。登録直後に「1週間分まとめて12冊」を
// 時間差入荷させるためのデータ。本命8＋セレンディピティ4（予約制廃止改定 2026-06-23・
// 週3回×4冊＝週12冊。本命2回×4冊=8冊＋日曜セレンディピティ1回×4冊=4冊）。
// 実パイプライン（Cloud Run/Vertex）接続前のデモ・mock用。firestoreモードでは
// 実生成に置き換わる（[[firestore-provider]] の runFirstRun → runPipeline）。
import type { Book } from "@publishr/shared-schema";

import type { InitialProfileInput } from "./profileOptions";

type Spec = {
  id: string;
  persona: string;
  title: string;
  subtitle: string;
  cover: string;
  reason: string;
};

// 本命（あなたの仕事・関心にまっすぐ応える）8冊（本命2回×4冊）。
const HONMEI: Spec[] = [
  { id: "fr_h01", persona: "p_kirishima", title: "30人を、ひとりで背負わない。", subtitle: "任せ方の設計図", cover: "b1", reason: "判断や相談が一人に集まりがちなチームで、任せる基準と権限の渡し方を整える一冊です。" },
  { id: "fr_h02", persona: "p_aoi", title: "叱らずに伝える", subtitle: "関係を壊さない指摘の作法", cover: "b2", reason: "相手との関係を守りながら、言いにくいことを具体的な改善につなげる伝え方を扱います。" },
  { id: "fr_h03", persona: "p_azumi", title: "\"問い\"で動かす現場", subtitle: "指示を減らし、自走を増やす", cover: "b3", reason: "指示待ちが増えた現場で、メンバーが自分で考え始める問いの作り方を整理します。" },
  { id: "fr_h04", persona: "p_yuki", title: "指示ゼロでも回る仕組み", subtitle: "属人化からの脱出", cover: "b4", reason: "人に頼りきった運用を、誰が見ても動ける仕組みに変えるための道筋を描きます。" },
  { id: "fr_h05", persona: "p_shiraishi", title: "数字で語るリーダー", subtitle: "感覚を、根拠に変える", cover: "b5", reason: "感覚や経験で語っていた判断を、数字と根拠で伝えられる形に変えていきます。" },
  { id: "fr_h06", persona: "p_yuki", title: "決めきる技術", subtitle: "迷いを断つ意思決定", cover: "b6", reason: "迷いが残る判断を、比較基準と撤退条件まで含めて決めきるための型に落とします。" },
  { id: "fr_h07", persona: "p_azumi", title: "1on1が変わる15分", subtitle: "聞き方だけで人は動く", cover: "b7", reason: "確認だけで終わりがちな1on1を、相手の考えと次の行動が見える時間に変えます。" },
  { id: "fr_h08", persona: "p_mikumo", title: "はじめての評価面談", subtitle: "納得を生むフィードバック設計", cover: "b8", reason: "評価の場を一方的な通達にせず、納得と次の成長につながる対話に整えます。" },
];

// セレンディピティ（関心の少し外側から視野を広げる）4冊（日曜1回×4冊）。
const SERENDIPITY: Spec[] = [
  { id: "fr_s01", persona: "p_kirishima", title: "茶室の経営学", subtitle: "\"間\"と\"余白\"の効用", cover: "b3", reason: "予定や判断を詰め込みすぎる日々に、余白を戦略として取り戻す視点をくれます。" },
  { id: "fr_s02", persona: "p_nanao", title: "登山隊に学ぶ撤退", subtitle: "引き返す勇気の作法", cover: "b6", reason: "続けるか退くかで迷う判断に、損切りではなく次を守る撤退の考え方を渡します。" },
  { id: "fr_s03", persona: "p_sengoku", title: "戦国の人材登用", subtitle: "適材適所の古典に学ぶ", cover: "b9", reason: "人をどう活かすかを、役割・場・タイミングの組み合わせから考え直します。" },
  { id: "fr_s04", persona: "p_kuroda", title: "あえて、決めない", subtitle: "保留という戦略", cover: "b2", reason: "すぐに結論を出すほど粗くなる問題に、あえて保留する判断の使いどころを示します。" },
];

const PREFACE =
  "この本は、いまのあなたの局面に合わせて書き下ろされました。最初の数ページは、あなたが日々感じている手応えのなさの正体から始めます。";

function buildBook(spec: Spec, shelf: Book["shelf"], kind: string): Book {
  return {
    id: spec.id,
    planId: "",
    status: "draft",
    authorPersonaId: spec.persona,
    title: spec.title,
    subtitle: spec.subtitle,
    coverVariant: spec.cover,
    coverUrl: null,
    shelf,
    estimatedChapters: 6,
    estimatedMinutes: 90,
    granularity: "full",
    prefaceSample: PREFACE,
    agenda: [],
    body: null,
    annotations: [],
    feedback: { readPercent: 0, dropped: false, rating: null, wantsSequel: false },
    kind,
    deliveryReason: spec.reason,
  };
}

/**
 * 初回の12冊（本命8＋セレンディピティ4）を返す。createdAt は付けない
 * （入荷時に呼び出し側で時間差スタンプする）。
 * profile があれば最初の本命の理由に関心を1つ織り込む（軽いパーソナライズ）。
 */
export function buildFirstRunBooks(profile?: InitialProfileInput | null): Book[] {
  const honmei = HONMEI.map((s) => buildBook(s, "arrivals", "honmei"));
  const serendipity = SERENDIPITY.map((s) => buildBook(s, "odd", "serendipity"));
  const top = profile?.recentInterests?.[0];
  if (top && honmei[0]) {
    honmei[0] = {
      ...honmei[0],
      deliveryReason: `${top}に向き合う人へ。${honmei[0].deliveryReason}`,
    };
  }
  return [...honmei, ...serendipity];
}

export const FIRST_RUN_TOTAL = HONMEI.length + SERENDIPITY.length; // 12（本命8＋セレンディピティ4）
