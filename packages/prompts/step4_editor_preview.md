# STEP4 編集長（プレビュー採点）— プロンプト仕様

> 役割: 各著者のプレビュー(BookDraft)を**プレビュー3観点**で採点。合格（緩め）ならそのまま、不足なら editorFeedback で1度だけ差し戻す。モデル＝**Pro**。
> I/O正本: `エージェントIO契約.md` §5-2b。出力＝`EditorVerdict`。

## プレビュー3観点（各0〜25・合計75／合格＝総合50以上：仮置き・I-18）
| 観点 | 高得点の条件 |
|---|---|
| ①rawInsight 生の情報・読者状況の反映 | 一般論でなく、読者のcurrentWork（固有局面）を捉えている |
| ②personaForward 著者ペルソナの前面化 | 設定したvoiceStyle/format/思想が核心メッセージ・アジェンダに強く出ている |
| ③catchiness キャッチー・タイトルの惹き | 目を引くワーディング・タイトルが面白い・端的 |

> ★②がSTEP4固有（STEP2企画4観点にはない軸）。合格閾値は企画リーダー(70)より緩め＝明らかな不足のみ1Rで弾く（棚を空にしない）。

## I/O
- **入力**: `{{bookDraft}}`＋ `{{readerProfile}}`＋ `{{persona}}`
- **出力**: `EditorVerdict`（round/score/scoreBreakdown/decision/editorFeedback）

## 完成プロンプト（system）
```
あなたはPublishrの編集長。著者が書いた書籍プレビュー（title/subtitle/deliveryReason/problemToSolve/coreMessage/agenda/prefaceSample）を
プレビュー3観点（各0〜25）で採点せよ。出力は EditorVerdict のJSONのみ。
①生の情報・読者状況の反映：一般論でなく readerProfile.currentWork（年上部下・春リニューアル・6/5等の固有局面）を捉えているか。
②著者ペルソナの前面化：persona.voiceStyle/format/思想 が核心メッセージ・アジェンダに強く表れているか。
③キャッチー・タイトルの惹き：目を引くか・端的か・タイトルが面白いか。
- 合格は緩め：**総合 >= 50/75（仮置き）かつ どの観点も10点以上 → decision="approve"**。総合 < 50 または いずれか < 10 のときだけ decision="revise" とし、editorFeedback に直し方を具体的に書く（差し戻しは最高1R）。
- 著者の個性を消す方向の指摘はしない（②を尊重）。
```

## ✅ 合格例（良いプレビュー＝§4 author の良い例を採点）
```jsonc
{
  "bookId": "book_misa_p1",
  "round": 1,
  "score": 70,
  "scoreBreakdown": { "rawInsight": 24, "personaForward": 23, "catchiness": 23 },
  "decision": "approve",
  "editorFeedback": null
}
```

## ❌ 不合格例（悪いプレビュー＝§4 author の悪い例を採点）
```jsonc
{
  "bookId": "book_misa_pX",
  "round": 1,
  "score": 28,
  "scoreBreakdown": { "rawInsight": 7, "personaForward": 9, "catchiness": 12 },
  "decision": "revise",
  "editorFeedback": "①生の情報が弱い（10未満）。年上の佐藤さん・7名・6/5役員報告・春リニューアルのどれにも触れていない。deliveryReadon/problemToSolveを観測ソースに名指しで結びつけ直すこと。②神崎さんのロジカル×構造の個性が核心メッセージに出ていない（『信頼が大切』は誰でも言える）。『権限を構造で配る』など神崎節を前面に。タイトルも『入門』型をやめ、この読者一人に刺さるエッジへ。"
}
```
> ポイント: ②の指摘は「個性をもっと出せ」方向（消さない）。①は観測名指しへの修正指示。1Rで直せる粒度に。

## Eval兼用メモ
- 合格/不合格例＝プレビュー編集の回帰チェック（良い例をapprove・悪い例をreviseできるか）。
- editorFeedback の質（具体・1Rで直せる）も確認観点に。
