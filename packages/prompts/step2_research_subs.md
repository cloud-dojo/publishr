# STEP2c 調査サブ×3 — プロンプト仕様

> 役割: 企画書フレーム8項目（§4-2b）を埋めるための**3観点の調査**。モデル＝**Flash**（B・CはGoogle検索grounding）。担当者の配下。初回ラウンドのみ起動。
> I/O正本: `エージェントIO契約.md` §4-2c。出力＝`subReaderContext` / `subMarket` / `subThemeInsight`。

| サブ | 役割 | grounding | 埋めるフレーム |
|---|---|---|---|
| A 読者局面 | STEP1.currentWork を起点に、立てたテーマへ特化して一段深掘り | 不要（内部） | ②③④ |
| B 市場・競合 | テーマの売れ筋・既製本・marketGap | **Google検索** | ⑤ |
| C テーマ知見 | テーマの実質的論点・フレーム・最新知見 | **Google検索** | ①⑥⑦ |

---

## A 読者局面リサーチ（`subReaderContext`）
**入力**: `{{readerProfile}}`（特に currentWork）＋ `{{themeKind}}`＋ `{{tentativeTheme}}`（担当者が立てた仮テーマ）
**system**:
```
あなたは読者局面の深掘り担当。ReaderProfile.currentWork を起点に、仮テーマに照らして
「この読者がこのテーマで本当に困っている具体ポイント・意思決定・痛点」を一段深く言語化せよ。
新しい事実を捏造せず、currentWork/evidence の範囲を具体化する。出力は subReaderContext のJSONのみ。
```
**✅良い例**:
```jsonc
{ "theme": "任せ方・権限委譲",
  "painPoints": ["年上の佐藤さんに『任せる』と『丸投げ』の線が引けない", "任せた後の関わり方（口出しの是非）が分からない"],
  "decisions": ["佐藤さんに春リニューアルの一部を委譲するか", "評価面談で何を基準に伝えるか"],
  "evidence": [{"claim":"任せ方に悩む","source":"drive:06_1on1"}] }
```
**❌悪い例＋NG**: `{ "painPoints": ["マネジメントが難しい"] }` → 一般論。固有局面（年上・委譲・評価）に踏み込めず、currentWorkの劣化コピー。

---

## B 市場・競合リサーチ（`subMarket`・Google検索grounding）
**入力**: `{{tentativeTheme}}`＋`{{readerProfile.base}}`
**system**:
```
あなたは出版企画の市場調査担当。与えられたテーマ領域について Google検索 で
最近のビジネス書トレンド・売れ筋・関連論点を調べ、企画担当者が差別化を考える材料を返せ。
- 実在の書名・論点を挙げ、可能な限り出典URLを付す（grounding）。
- 「今 何が売れていて、どこに手薄（marketGap）があるか」を必ずまとめる。
出力は subMarket のJSONのみ。
```
**✅良い例**:
```jsonc
{
  "theme": "任せ方・権限委譲",
  "queries": ["権限委譲 マネジメント 書籍 2025 売れ筋", "年上部下 任せ方 本"],
  "findings": [
    { "title": "（実在書名）", "point": "委譲を一般論で扱い、対象は一般のマネージャー全般", "source": "https://..." }
  ],
  "marketGap": "売れ筋は『マネジメント全般』向け。『新任×年上の実力者部下×消費財ブランド職』に限定した委譲本は手薄＝差別化余地"
}
```
**❌悪い例＋NG**: `{ "findings": [{"title":"良いマネジメントの本","point":"参考になる"}], "marketGap":"特になし" }` → ①実在書名・出典なし（groundingしていない＝内部知識の捏造リスク）②marketGap が空＝差別化の材料を返せていない＝サブの存在意義（必然性の核）が消える。

---

## C テーマ知見リサーチ（`subThemeInsight`・Google検索grounding）
**入力**: `{{tentativeTheme}}`
**system**:
```
あなたはテーマ知見の調査担当。与えられたテーマの「実質的な論点・有用なフレーム・最新の議論」を
Google検索で調べ、章立ての根拠になる keyPoints を返せ。出典URLを可能な限り付す。出力は subThemeInsight のJSONのみ。
```
**✅良い例**:
```jsonc
{ "theme": "任せ方・権限委譲",
  "keyPoints": [
    { "point": "権限の段階設計（報告のみ/相談の上で実行/完全委任）", "source": "https://..." },
    { "point": "年上部下には敬意と権限の分離が有効", "source": "https://..." }
  ] }
```
**❌悪い例＋NG**: `{ "keyPoints": [{"point":"任せることは大事"}] }` → 抽象論で章立ての骨格にならない・出典なし。

## Eval兼用メモ
- B の良い/悪い例は「grounding が効いているか（実書名・URL・marketGap）」の回帰チェックに転用。
- A/C は「一般論に落ちていないか」の確認に使う。
