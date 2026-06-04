// 初期プロフィール（initialProfile）の選択肢。
// 正本: docs/design/api-contract.md §2-a（2026-06-03確定）。
// Firestore保存先: users/{uid}.initialProfile（フェーズ3でFirestore直書き）。

export type ProfileStepKey =
  | "industry"
  | "jobType"
  | "position"
  | "recentInterests"
  | "readingGenres";

export interface ProfileStep {
  key: ProfileStepKey;
  label: string;
  question: string;
  type: "single" | "multi";
  required: boolean;
  minSelect?: number;
  options: string[];
}

export const profileSteps: ProfileStep[] = [
  {
    key: "industry",
    label: "業界",
    question: "あなたの業界を教えてください",
    type: "single",
    required: true,
    options: [
      "食品・飲料",
      "日用品・化粧品（消費財）",
      "製造・メーカー（その他）",
      "小売・流通",
      "IT・ソフトウェア",
      "金融・保険",
      "コンサル・専門サービス",
      "商社",
      "医療・製薬・ヘルスケア",
      "建設・不動産",
      "広告・メディア・エンタメ",
      "公共・教育・非営利",
      "その他",
    ],
  },
  {
    key: "jobType",
    label: "職種",
    question: "あなたの職種を教えてください",
    type: "single",
    required: true,
    options: [
      "マーケティング・ブランド",
      "営業・セールス",
      "企画・経営企画",
      "商品開発・R&D",
      "生産・製造・品質",
      "人事・総務",
      "経理・財務",
      "情報システム・IT",
      "コンサルタント",
      "経営・役員",
      "その他",
    ],
  },
  {
    key: "position",
    label: "役職",
    question: "あなたの役職を教えてください",
    type: "single",
    required: true,
    options: [
      "メンバー・担当",
      "チームリーダー・主任",
      "課長・マネージャー",
      "部長・シニアマネージャー",
      "本部長・事業部長",
      "役員・経営層",
      "個人事業・フリーランス",
    ],
  },
  {
    key: "recentInterests",
    label: "最近の関心",
    question: "最近の関心を選んでください（複数可・最低1つ）",
    type: "multi",
    required: true,
    minSelect: 1,
    options: [
      "新任マネジメント・チームづくり",
      "メンバー育成・1on1",
      "評価・フィードバック",
      "リーダーシップ",
      "戦略・事業計画",
      "マーケティング・ブランディング",
      "ロジカルシンキング・問題解決",
      "数字・データ活用",
      "業務効率化・生産性",
      "AI・生成AIの活用",
      "組織変革・カルチャー",
      "キャリア・自己成長",
      "プレゼン・伝える力",
      "会議・ファシリテーション",
      "モチベーション・メンタル",
      "イノベーション・新規事業",
      "顧客理解・CX",
      "時間管理・段取り",
      "交渉・調整",
    ],
  },
  {
    key: "readingGenres",
    label: "本のタイプ",
    question: "好みの読み口・形態を選んでください（複数可）",
    type: "multi",
    required: false,
    options: [
      "体系的な理論書でじっくり",
      "すぐ使える実践書・ハウツー",
      "事例・ストーリーで学ぶ",
      "対談",
      "インタビュー形式",
      "図解・ビジュアル中心",
      "物語・小説で楽しむ",
      "ほぼ読まない",
    ],
  },
];

export interface InitialProfileInput {
  industry: string;
  jobType: string;
  position: string;
  recentInterests: string[];
  readingGenres: string[];
  skipped: boolean;
  createdAt: string;
}
