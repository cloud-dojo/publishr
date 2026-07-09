import type { Book } from "./types";

export const OWNER = "misa";

/*
 * 書籍シード。佐倉美咲（食品メーカー新任マーケ課長）の棚。
 * draft=今週の入荷 / reserved=予約中 / writing=執筆中 / published=既読。
 * 表紙は coverFamily（CSSグラデ）で描画。
 */

export const books: Book[] = [
  /* ===== 今週の入荷（draft） ===== */
  {
    bookId: "b_deleg",
    ownerUid: OWNER,
    title: "30人を、ひとりで背負わない。",
    subtitle: "任せ方を、設計する",
    coverFamily: "navy",
    status: "draft",
    themeKind: "honmei",
    authorPersonaId: "p01",
    planId: "plan_deleg",
    prefaceSample:
      "佐倉さん、あなたはいま、30人を一枚の地図に描こうとしている。今度はその地図の上に、「どこまでを誰が描くか」の線を引いていない。これが本書の核心だ。",
  },
  {
    bookId: "b02",
    ownerUid: OWNER,
    title: "“問い”で動かす現場",
    subtitle: "答えより、問いの設計を",
    coverFamily: "green",
    status: "draft",
    themeKind: "honmei",
    authorPersonaId: "p11",
    planId: "plan_facil",
    prefaceSample:
      "良い会議の前に、良い問いがある。あなたが沈黙を恐れる限り、チームは考えることをやめる。",
  },
  {
    bookId: "b03",
    ownerUid: OWNER,
    title: "指示ゼロでも回る仕組み",
    subtitle: "自走するチームの設計",
    coverFamily: "ink",
    status: "draft",
    themeKind: "honmei",
    authorPersonaId: "p03",
    planId: "plan_deleg",
    prefaceSample:
      "あなたがいなくても回る——それは無責任ではない。むしろ、最も責任ある設計だ。",
  },
  {
    bookId: "b04",
    ownerUid: OWNER,
    title: "数字で語るリーダー",
    subtitle: "感想を、エビデンスに変える",
    coverFamily: "ink",
    status: "draft",
    themeKind: "honmei",
    authorPersonaId: "p04",
    planId: "plan_facil",
    prefaceSample:
      "「なんとなく良い」では、人は動かない。再現性のある言葉で、チームの意思決定の質を上げよう。",
  },
  {
    bookId: "b_age",
    ownerUid: OWNER,
    title: "年上の部下と、どう働くか",
    subtitle: "経験への敬意と、権限の両立",
    coverFamily: "green",
    status: "draft",
    themeKind: "honmei",
    authorPersonaId: "p03",
    planId: "plan_deleg",
    prefaceSample:
      "年齢は、上下ではない。経験という資産を、どう活かすかという設計の問題だ。",
  },

  {
    bookId: "b05",
    ownerUid: OWNER,
    title: "あなたの月曜が変わる5つの会話",
    subtitle: "新任マネージャーの、静かな物語",
    coverFamily: "gold",
    status: "draft",
    themeKind: "serendipity",
    authorPersonaId: "p10",
    planId: "plan_deleg",
    prefaceSample:
      "月曜の朝、彼女はまだ答えを持っていなかった。けれど、ひとつの会話が、週を変えた。",
  },
  {
    bookId: "b_tea",
    ownerUid: OWNER,
    title: "余白という戦略",
    subtitle: "速さの時代に、立ち止まる力",
    coverFamily: "brown",
    status: "draft",
    themeKind: "serendipity",
    authorPersonaId: "p07",
    planId: "plan_brand",
    prefaceSample:
      "効率の反対は、無駄ではない。余白だ。問いを生きる者にだけ、深さが宿る。",
  },
  {
    bookId: "b_hist",
    ownerUid: OWNER,
    title: "歴史に学ぶ、決断の作法",
    subtitle: "合意なき時代の、まとめ方",
    coverFamily: "ink",
    status: "draft",
    themeKind: "serendipity",
    authorPersonaId: "p12",
    planId: "plan_facil",
    prefaceSample:
      "決断とは、反対を呑み込むことだ。歴史は、その繰り返しでできている。",
  },

  /* ===== 予約中（reserved） ===== */
  {
    bookId: "b_decide",
    ownerUid: OWNER,
    title: "決めきる技術",
    subtitle: "速い失敗は、遅い正解に勝つ",
    coverFamily: "navy",
    status: "reserved",
    themeKind: "honmei",
    authorPersonaId: "p05",
    planId: "plan_facil",
    prefaceSample: "完璧な計画より、速い検証。動かないことが、最大のリスクだ。",
  },
  {
    bookId: "b07",
    ownerUid: OWNER,
    title: "ブランド再生の意思決定",
    subtitle: "意味が伝わった商品が、選ばれる",
    coverFamily: "wine",
    status: "reserved",
    themeKind: "honmei",
    authorPersonaId: "p06",
    planId: "plan_brand",
    prefaceSample:
      "リニューアルとは、パッケージを変えることではない。約束を、結び直すことだ。",
  },
  {
    bookId: "b09",
    ownerUid: OWNER,
    title: "会議を半分にする問い",
    subtitle: "準備で9割が決まる",
    coverFamily: "green",
    status: "reserved",
    themeKind: "honmei",
    authorPersonaId: "p11",
    planId: "plan_facil",
    prefaceSample: "その会議は、本当に集まる必要があったか。問いがあれば、半分は消える。",
  },

  /* ===== 既読（published） ===== */
  {
    bookId: "b08",
    ownerUid: OWNER,
    title: "最初の100日の設計図",
    subtitle: "新任マネージャーの着任設計",
    coverFamily: "navy",
    status: "published",
    themeKind: "honmei",
    authorPersonaId: "p03",
    planId: "plan_deleg",
    prefaceSample: "最初の100日で、あなたは「何をするか」より「どう在るか」を試される。",
    feedback: { rating: 5, read: 100, wantsSequel: true },
  },
  {
    bookId: "b10",
    ownerUid: OWNER,
    title: "現場が自走する組織",
    subtitle: "町工場の再建に学ぶ",
    coverFamily: "green",
    status: "published",
    themeKind: "honmei",
    authorPersonaId: "p02",
    planId: "plan_deleg",
    prefaceSample: "理屈はええ。まず自分が動く。現場が動いた瞬間を、俺は何度も見てきた。",
    feedback: { rating: 4, read: 100 },
  },
  {
    bookId: "b13",
    ownerUid: OWNER,
    title: "フィードバックの技術",
    subtitle: "評価面談を、成長の場に変える",
    coverFamily: "wine",
    status: "published",
    themeKind: "honmei",
    authorPersonaId: "p04",
    planId: "plan_facil",
    prefaceSample: "評価とは、過去を裁くことではない。未来の行動を、設計することだ。",
    feedback: { rating: 5, read: 100 },
  },
  {
    bookId: "b11",
    ownerUid: OWNER,
    title: "茶室の経営学",
    subtitle: "速さの時代の、立ち止まる力",
    coverFamily: "brown",
    status: "published",
    themeKind: "serendipity",
    authorPersonaId: "p07",
    planId: "plan_brand",
    prefaceSample: "一服の茶に、経営のすべてがある。もてなしとは、相手の文脈を読むことだ。",
    feedback: { rating: 4, read: 80 },
  },
  {
    bookId: "b12",
    ownerUid: OWNER,
    title: "群像の大局観",
    subtitle: "合意形成の歴史に学ぶ",
    coverFamily: "ink",
    status: "published",
    themeKind: "serendipity",
    authorPersonaId: "p12",
    planId: "plan_facil",
    prefaceSample: "決断とは、反対を呑み込むことだ。歴史は、その繰り返しでできている。",
    feedback: { rating: 3, read: 60 },
  },
];

export const bookById = (id: string): Book | undefined =>
  books.find((b) => b.bookId === id);
