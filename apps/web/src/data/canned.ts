// mockモード（API不要）用のキャンドデータ。Python側 publishr_agents/canned.py と一致。
import type {
  Observation,
  PlanningCandidate,
  ReaderProfile,
  RejectLogEntry,
} from "@publishr/shared-schema";

export const CANNED_OBSERVATION: Observation = {
  noteCount: 7,
  topLabels: ["マネジメント", "所感", "1on1", "ブランド戦略", "リニューアル"],
  signals: ["年上部下との距離感", "初の評価面談への不安", "ブランドリニューアルの意思決定", "積読の増加"],
};

export const CANNED_READER_PROFILE: ReaderProfile = {
  role: "食品・飲料・マーケティング課長／部下7名",
  situation: "2026年4月に昇格したばかりの新任マネージャー。部下7名（年上ベテランの佐藤さんを含む）を率いながら、担当ブランド「しずく天然水」のリニューアル進行という2つの局面を同時に抱えている。",
  interests: ["ピープルマネジメント", "年上部下との関係", "ブランド戦略", "評価・フィードバック"],
  signals: CANNED_OBSERVATION.signals,
  serendipityTolerance: "中",
};

export const CANNED_CANDIDATES: PlanningCandidate[] = [
  { key: "practical", persona: "実務直撃型", candidate: "任せ方の設計図", planId: "plan_makase" },
  { key: "framework", persona: "フレームワーク型", candidate: "問いで動かす現場", planId: "plan_toi" },
  { key: "contrarian", persona: "逆張り型", candidate: "あえて抱え込め", planId: "plan_shijizero" },
];

export const CANNED_APPROVED_PLAN_IDS = ["plan_makase", "plan_toi"];

export const CANNED_DEBATE: RejectLogEntry[] = [
  { round: 1, candidate: "任せ方の設計図", persona: "実務直撃型", verdict: "却下", reason: "方向性は良いが具体性が不足。年上部下のいる新任マネージャーの局面に寄せて再提出せよ。" },
  { round: 1, candidate: "問いで動かす現場", persona: "フレームワーク型", verdict: "却下", reason: "一般論に寄りすぎ。既製書との差別化を出して再提出。" },
  { round: 1, candidate: "あえて抱え込め", persona: "逆張り型", verdict: "却下", reason: "逆張りの意図は買うが論拠が粗い。根拠を添えて再提出。" },
  { round: 2, candidate: "任せ方の設計図", persona: "実務直撃型", verdict: "採用", reason: "局面に最も的中。年上部下を含む新任マネージャーの『任せ方』に直結。" },
  { round: 2, candidate: "問いで動かす現場", persona: "フレームワーク型", verdict: "採用", reason: "指示を減らす問いの設計が、年上部下への関わり方の課題にも接続している。" },
  { round: 2, candidate: "あえて抱え込め", persona: "逆張り型", verdict: "保留", reason: "視点は鋭いが時期尚早。次回の候補として保留。" },
];

// mockモードで「執筆」後に入る本文（デモ本）。authoring.py の _MAKASE_BODY 相当。
export function cannedBody(bookId: string): string {
  if (bookId === "b_makasekata") {
    return [
      "## 第3章 権限の設計図",
      "",
      "佐倉さん。前の章で、あなたのチームを一枚の地図に描いた。今度はその地図の上に、「どこまで渡すか」の線を引いていく。これが本書の核心だ。",
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
