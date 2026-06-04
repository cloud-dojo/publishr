/*
 * 初期登録（initialProfile）の選択肢。UI仕様書 §3-2 の叩き台に準拠（G1-9・W1で最終確定）。
 * 実装では users/{uid}.initialProfile へ直書きする。
 */

export interface ProfileStep {
  key: "industry" | "jobType" | "position" | "recentInterests" | "readingGenres";
  num: string; // "1/5"
  title: string; // 質問文
  caption: string;
  multi: boolean; // 複数選択か
  required: boolean;
  options: string[];
}

export const profileSteps: ProfileStep[] = [
  {
    key: "industry",
    num: "1/5",
    title: "あなたの業界は？",
    caption: "いちばん近いものをひとつ選んでください。",
    multi: false,
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
    num: "2/5",
    title: "あなたの職種は？",
    caption: "いちばん近いものをひとつ選んでください。",
    multi: false,
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
    num: "3/5",
    title: "あなたの役職は？",
    caption: "いちばん近いものをひとつ選んでください。",
    multi: false,
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
    num: "4/5",
    title: "最近、関心のあることは？",
    caption: "あてはまるものをすべて選んでください（最低1つ）。",
    multi: true,
    required: true,
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
    // ※キーは readingGenres のまま据え置き。内容は「ジャンル」ではなく「読み口・形態」（G1-9確定・リネームはMVP対象外）。
    key: "readingGenres",
    num: "5/5",
    title: "どんなタイプの本が好きですか？",
    caption: "好きな読み口を選んでください（複数可）",
    multi: true,
    required: false,
    options: [
      "体系的な理論書でじっくり",
      "すぐ使える実践書・ハウツー",
      "事例・ストーリーで学ぶ",
      "対談／インタビュー形式",
      "図解・ビジュアル中心",
      "物語・小説で楽しむ",
      "ほぼ読まない",
    ],
  },
];
