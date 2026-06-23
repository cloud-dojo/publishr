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
  { id: "fr_h01", persona: "p_kirishima", title: "30人を、ひとりで背負わない。", subtitle: "任せ方の設計図", cover: "b1", reason: "「全員の判断を自分が抱えている」局面に向けて、権限の設計から書き下ろしました。" },
  { id: "fr_h02", persona: "p_aoi", title: "叱らずに伝える", subtitle: "関係を壊さない指摘の作法", cover: "b2", reason: "年上部下との距離感に揺れるいま、指摘を「対立」にしない伝え方をまとめました。" },
  { id: "fr_h03", persona: "p_azumi", title: "\"問い\"で動かす現場", subtitle: "指示を減らし、自走を増やす", cover: "b3", reason: "指示より「問い」が効く局面だと読みました。現場が自分で動き出す設計です。" },
  { id: "fr_h04", persona: "p_yuki", title: "指示ゼロでも回る仕組み", subtitle: "属人化からの脱出", cover: "b4", reason: "任せられない状態が続くシグナルが見えます。仕組みで回す道筋を描きました。" },
  { id: "fr_h05", persona: "p_shiraishi", title: "数字で語るリーダー", subtitle: "感覚を、根拠に変える", cover: "b5", reason: "上申・報告の準備メモが気になっています。方向性を定量で語る準備の一冊です。" },
  { id: "fr_h06", persona: "p_yuki", title: "決めきる技術", subtitle: "迷いを断つ意思決定", cover: "b6", reason: "意思決定があなたに集中している局面に、決めきるための型を用意しました。" },
  { id: "fr_h07", persona: "p_azumi", title: "1on1が変わる15分", subtitle: "聞き方だけで人は動く", cover: "b7", reason: "1on1の負荷増の記述が増えています。短く深い対話に変える実践書です。" },
  { id: "fr_h08", persona: "p_mikumo", title: "はじめての評価面談", subtitle: "納得を生むフィードバック設計", cover: "b8", reason: "評価面談への不安が見えます。納得を生む準備と言葉を組み立てました。" },
];

// セレンディピティ（関心の少し外側から視野を広げる）4冊（日曜1回×4冊）。
const SERENDIPITY: Spec[] = [
  { id: "fr_s01", persona: "p_kirishima", title: "茶室の経営学", subtitle: "\"間\"と\"余白\"の効用", cover: "b3", reason: "余白の設計という視点から、いまの忙しさを問い直す一冊です。" },
  { id: "fr_s02", persona: "p_nanao", title: "登山隊に学ぶ撤退", subtitle: "引き返す勇気の作法", cover: "b6", reason: "「やめ方」の意思決定を、別の世界の実話から学びます。" },
  { id: "fr_s03", persona: "p_sengoku", title: "戦国の人材登用", subtitle: "適材適所の古典に学ぶ", cover: "b9", reason: "人をどう配するか——歴史の決断から、いまの配置を考え直します。" },
  { id: "fr_s04", persona: "p_kuroda", title: "あえて、決めない", subtitle: "保留という戦略", cover: "b2", reason: "すぐ決める習慣の逆を行く、保留の使いどころを説いた逆張りの一冊。" },
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
      deliveryReason: `直近のメモに「${top}」への関心が見えます。${honmei[0].deliveryReason}`,
    };
  }
  return [...honmei, ...serendipity];
}

export const FIRST_RUN_TOTAL = HONMEI.length + SERENDIPITY.length; // 12（本命8＋セレンディピティ4）
