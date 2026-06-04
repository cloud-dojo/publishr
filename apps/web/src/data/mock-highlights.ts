// ハイライト・付箋のモックデータ。
// フェーズ3では Firestore `users/{uid}.readingFB.highlights[]` 購読に差し替える
// （[[firestore-provider]] の seam）。それまでの画面確認用の暫定データ。
// bookId は fixtures の蔵書（shelf=library）に対応させている。

export type HighlightKind = "highlight" | "note" | "bookmark";

export interface MockHighlight {
  id: string;
  bookId: string;
  kind: HighlightKind;
  text: string;
  chapter?: string;
  note?: string;
  tags: string[];
}

export const MOCK_HIGHLIGHTS: MockHighlight[] = [
  {
    id: "h1",
    bookId: "b_100nichi",
    kind: "highlight",
    text: "最初の100日は、成果ではなく「信頼の設計図」を引く期間だと考える。",
    chapter: "Chapter 02 ・ 着任の作法",
    tags: ["組織設計", "リーダーシップ"],
  },
  {
    id: "h2",
    bookId: "b_100nichi",
    kind: "note",
    text: "「能力ではなく設計の問題」——ここは自分のチームにそのまま当てはまる。",
    chapter: "Chapter 05 ・ 権限の設計図",
    note: "来週の1on1で、権限委譲の線引きを見直す。",
    tags: ["権限委譲", "仕組み化"],
  },
  {
    id: "h3",
    bookId: "b_jiso",
    kind: "highlight",
    text: "現場が自走するのは、放任の結果ではなく、判断基準を共有した結果である。",
    chapter: "Chapter 03 ・ 基準の言語化",
    tags: ["自律", "判断基準"],
  },
  {
    id: "h4",
    bookId: "b_jiso",
    kind: "bookmark",
    text: "「任せる」と「丸投げ」を分けるチェックリスト",
    chapter: "Chapter 07",
    tags: ["権限委譲"],
  },
  {
    id: "h5",
    bookId: "b_kaigi",
    kind: "highlight",
    text: "良い会議は「決める会議」と「考える会議」を混ぜない。",
    chapter: "Chapter 01 ・ 会議の種類",
    tags: ["会議", "意思決定"],
  },
  {
    id: "h6",
    bookId: "b_kaigi",
    kind: "note",
    text: "問いの設計次第で、同じメンバーでも出てくる答えが変わる。",
    chapter: "Chapter 04 ・ 問いの立て方",
    note: "次回の定例、アジェンダを「問い」の形に書き換えてみる。",
    tags: ["問い", "ファシリテーション"],
  },
  {
    id: "h7",
    bookId: "b_dokusho",
    kind: "highlight",
    text: "リーダーの読書は、答えを探す行為ではなく、問いを増やす行為だ。",
    chapter: "Chapter 02",
    tags: ["読書", "自己成長"],
  },
  {
    id: "h8",
    bookId: "b_dokusho",
    kind: "bookmark",
    text: "積読を「思考の在庫」として肯定する考え方",
    chapter: "Chapter 06",
    tags: ["読書"],
  },
];

export function highlightsByKind(kind: HighlightKind | "all"): MockHighlight[] {
  return kind === "all" ? MOCK_HIGHLIGHTS : MOCK_HIGHLIGHTS.filter((h) => h.kind === kind);
}

export interface HighlightGroup {
  bookId: string;
  items: MockHighlight[];
}

export function highlightsGroupedByBook(kind: HighlightKind | "all"): HighlightGroup[] {
  const groups = new Map<string, MockHighlight[]>();
  for (const h of highlightsByKind(kind)) {
    const list = groups.get(h.bookId) ?? [];
    list.push(h);
    groups.set(h.bookId, list);
  }
  return [...groups.entries()].map(([bookId, items]) => ({ bookId, items }));
}

export function highlightTagCloud(): { tag: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const h of MOCK_HIGHLIGHTS) {
    for (const t of h.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);
}
