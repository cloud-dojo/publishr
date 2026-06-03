// mockモード（API不要）用のキャンドデータ。Python側 publishr_agents/canned.py と一致。
import type { Observation, ReaderProfile, RejectLogEntry } from "@publishr/shared-schema";

export const CANNED_OBSERVATION: Observation = {
  noteCount: 7,
  topLabels: ["マネジメント", "所感", "1on1", "組織", "体制"],
  signals: ["管掌範囲の拡大", "1on1の負荷増", "属人化の懸念", "定量報告の要請"],
};

export const CANNED_READER_PROFILE: ReaderProfile = {
  role: "製造業・製造課長／30名を統括",
  situation: "10名から30名規模への移行期。情報と意思決定が本人に集中し、現場が止まりはじめている局面。",
  interests: ["権限委譲", "属人化の解消", "意思決定", "1on1の負荷"],
  signals: CANNED_OBSERVATION.signals,
  serendipityTolerance: "中",
};

export const CANNED_DEBATE: RejectLogEntry[] = [
  { round: 1, candidate: "任せ方の設計図", persona: "実務直撃型", verdict: "却下", reason: "方向性は良いが具体性が不足。30名の局面に寄せて再提出せよ。" },
  { round: 1, candidate: "権限委譲5原則", persona: "フレームワーク型", verdict: "却下", reason: "一般論に寄りすぎ。既製書との差別化を出して再提出。" },
  { round: 1, candidate: "あえて抱え込め", persona: "逆張り型", verdict: "却下", reason: "逆張りの意図は買うが論拠が粗い。根拠を添えて再提出。" },
  { round: 2, candidate: "任せ方の設計図", persona: "実務直撃型", verdict: "採用", reason: "局面に最も的中。30名移行期の『任せ方』に直結。" },
  { round: 2, candidate: "権限委譲5原則", persona: "フレームワーク型", verdict: "却下", reason: "依然として一般論。あなたの現場への接続が弱い。" },
  { round: 2, candidate: "あえて抱え込め", persona: "逆張り型", verdict: "保留", reason: "視点は鋭いが時期尚早。次回の候補として保留。" },
];

// mockモードで「執筆」後に入る本文（デモ本）。authoring.py の _MAKASE_BODY 相当。
export function cannedBody(bookId: string): string {
  if (bookId === "b_makasekata") {
    return [
      "## 第3章 権限の設計図",
      "",
      "田所さん。前の章で、あなたの30人を一枚の地図に描いた。今度はその地図の上に、「どこまで渡すか」の線を引いていく。これが本書の核心だ。",
      "",
      "多くのリーダーが委譲でつまずくのは、能力の問題ではない。渡す範囲を「気分」で決めているからだ。",
      "",
      "そこで、あなたの現場に合わせた三層モデルを提案したい。第一層は「報告のみ」、第二層は「相談の上で実行」、第三層は「完全に委ねる」。",
      "",
      "結論から言う。任せられないのは、あなたの度量の問題ではない。設計の問題だ。",
    ].join("\n");
  }
  return "## 第1章\n\n（この本の本文サンプル）";
}
