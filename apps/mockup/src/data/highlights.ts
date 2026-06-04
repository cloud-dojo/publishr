import type { Highlight } from "./types";

/*
 * ハイライト・付箋・ブックマーク（users/{uid}.readingFB.highlights[]）。
 * 全20件。タブ「すべて 20」と整合。書籍別にグルーピングして表示する。
 */

export const highlights: Highlight[] = [
  /* b_deleg: 30人を、ひとりで背負わない。 */
  {
    id: "h01",
    bookId: "b_deleg",
    kind: "note",
    text: "渡す範囲を「気分」で決めている",
    chapter: "02 「任せられない」の正体",
    note: "ここ、自分のことだ。佐藤さんへの依頼がいつも曖昧なのは、範囲を設計してないから。",
    tags: ["権限委譲", "任せ方"],
    savedAt: "2026-05-28T09:12:00+09:00",
  },
  {
    id: "h02",
    bookId: "b_deleg",
    kind: "highlight",
    text: "この器は固定ではない。四半期ごとに引き直してよい",
    chapter: "04 権限の三層モデル",
    tags: ["権限委譲", "設計"],
    savedAt: "2026-05-28T09:20:00+09:00",
  },
  {
    id: "h03",
    bookId: "b_deleg",
    kind: "highlight",
    text: "「任せる」とは仕事を渡すことでなく、設計すること",
    chapter: "05 権限の設計図",
    tags: ["任せ方", "リーダーシップ"],
    savedAt: "2026-05-28T09:28:00+09:00",
  },
  {
    id: "h04",
    bookId: "b_deleg",
    kind: "bookmark",
    text: "「あなたはどう思う？」を一日五回",
    chapter: "06 任せたあとの、関わり方",
    tags: ["問いかけ", "1on1"],
    savedAt: "2026-05-28T09:40:00+09:00",
  },
  {
    id: "h05",
    bookId: "b_deleg",
    kind: "highlight",
    text: "敬意と権限は両立する。年齢は、設計の変数のひとつにすぎない",
    chapter: "03 年上の部下に、どう任せるか",
    tags: ["年上の部下", "敬意"],
    savedAt: "2026-05-28T09:48:00+09:00",
  },
  {
    id: "h06",
    bookId: "b_deleg",
    kind: "note",
    text: "口は出さない、目は離さない",
    chapter: "06 任せたあとの、関わり方",
    note: "壁に貼っておきたい言葉。",
    tags: ["任せ方"],
    savedAt: "2026-05-28T10:02:00+09:00",
  },

  /* b09: 会議を半分にする問い */
  {
    id: "h07",
    bookId: "b09",
    kind: "highlight",
    text: "指示は違いを、問いは違いを活かす。違うを潰す勇気がリーダーを育てる",
    chapter: "01 なぜ、その会議は決まらないのか",
    tags: ["会議", "問い"],
    savedAt: "2026-05-24T14:10:00+09:00",
  },
  {
    id: "h08",
    bookId: "b09",
    kind: "highlight",
    text: "沈黙は、空白ではない。最も雄弁な情報である",
    chapter: "02 沈黙は、情報である",
    tags: ["会議", "ファシリ"],
    savedAt: "2026-05-24T14:22:00+09:00",
  },
  {
    id: "h09",
    bookId: "b09",
    kind: "note",
    text: "会議は準備で9割決まる",
    chapter: "04 準備で9割が決まる",
    note: "来週の定例、アジェンダを問いの形に書き換えてみる。",
    tags: ["会議", "準備"],
    savedAt: "2026-05-24T14:35:00+09:00",
  },
  {
    id: "h10",
    bookId: "b09",
    kind: "bookmark",
    text: "「決める会議」と「広げる会議」を混ぜない",
    chapter: "03 問いの設計図",
    tags: ["会議設計"],
    savedAt: "2026-05-24T14:50:00+09:00",
  },

  /* b08: 最初の100日の設計図 */
  {
    id: "h11",
    bookId: "b08",
    kind: "highlight",
    text: "最初の100日は、成果より「信頼の残高」を積む期間だ",
    chapter: "01 着任の作法",
    tags: ["新任", "信頼"],
    savedAt: "2026-05-18T20:05:00+09:00",
  },
  {
    id: "h12",
    bookId: "b08",
    kind: "highlight",
    text: "何をするかより、どう在るかを、人は見ている",
    chapter: "02 在り方の設計",
    tags: ["新任", "リーダーシップ"],
    savedAt: "2026-05-18T20:18:00+09:00",
  },
  {
    id: "h13",
    bookId: "b08",
    kind: "note",
    text: "10年先から逆算して、いま決める",
    chapter: "05 長期の視点",
    note: "短期の数字に追われすぎている自覚あり。",
    tags: ["長期視点"],
    savedAt: "2026-05-18T20:30:00+09:00",
  },

  /* b13: フィードバックの技術 */
  {
    id: "h14",
    bookId: "b13",
    kind: "highlight",
    text: "評価とは過去を裁くことでなく、未来の行動を設計すること",
    chapter: "01 評価の再定義",
    tags: ["評価面談", "FB"],
    savedAt: "2026-05-12T19:40:00+09:00",
  },
  {
    id: "h15",
    bookId: "b13",
    kind: "highlight",
    text: "人ではなく、行動を語れ。事実と解釈を分けよ",
    chapter: "02 伝え方の原則",
    tags: ["FB", "評価面談"],
    savedAt: "2026-05-12T19:52:00+09:00",
  },
  {
    id: "h16",
    bookId: "b13",
    kind: "bookmark",
    text: "ポジティブ・フィードバックも「具体」でなければ届かない",
    chapter: "03 承認の技術",
    tags: ["FB", "承認"],
    savedAt: "2026-05-12T20:05:00+09:00",
  },

  /* b10: 現場が自走する組織 */
  {
    id: "h17",
    bookId: "b10",
    kind: "highlight",
    text: "理屈より、まず自分が動く。背中は、どんな号令より速い",
    chapter: "01 再建の初日",
    tags: ["現場", "率先"],
    savedAt: "2026-05-06T21:15:00+09:00",
  },
  {
    id: "h18",
    bookId: "b10",
    kind: "note",
    text: "失敗を隠す組織は、二度同じ失敗をする",
    chapter: "03 失敗を晒す文化",
    note: "心理的安全性、まさにこれ。チームで共有したい。",
    tags: ["現場", "心理的安全性"],
    savedAt: "2026-05-06T21:28:00+09:00",
  },

  /* b11: 茶室の経営学 */
  {
    id: "h19",
    bookId: "b11",
    kind: "highlight",
    text: "もてなしとは、相手の文脈を読むことだ",
    chapter: "02 一期一会の設計",
    tags: ["教養", "ブランド"],
    savedAt: "2026-04-29T22:10:00+09:00",
  },

  /* b12: 群像の大局観 */
  {
    id: "h20",
    bookId: "b12",
    kind: "highlight",
    text: "百の正論より、一つの合意。決断とは反対を呑み込むことだ",
    chapter: "01 合意という技術",
    tags: ["合意形成", "教養"],
    savedAt: "2026-04-22T22:40:00+09:00",
  },
];
