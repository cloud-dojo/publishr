# packages/prompts — Publishr エージェント プロンプト仕様

> **位置づけ**: 各エージェントの**完成形プロンプト**＋**良い/悪い出力例**を1ファイル＝1エージェントで管理する。鉄田担当（基準1の質）。一瀬のランタイム実装（`agents/*.py`）はここのプロンプトを読み込んで使う。
> **真実源**: 役割・I/Oスキーマの正本は [`設計資料/エージェントIO契約.md`](../../docs/design/agent-io-contract.md)。本フォルダは**スキーマを重複させず**、プロンプト本文と例に集中する。
> **構造の同期メモ**: [`設計資料/エージェント責務サマリー.md`](../../docs/design/agent-responsibilities.md)。

---

## 共通方針

1. **変数記法**: プロンプト内の差し込みは `{{変数名}}`（例 `{{readerProfile}}`・`{{approvedPlan}}`・`{{persona}}`）。ランタイムが実値を注入する。
2. **出力は必ず指定スキーマのJSONのみ**（前置き・後置きの散文を出さない）。スキーマ定義は IO契約 §該当節を参照。ADKの構造化出力で強制。
3. **例の統一ベース＝デモペルソナ「佐倉 美咲」**（食品メーカー マルミナ食品・マーケ課長/2026-04新任・部下7名・年上の佐藤健一42歳・「しずく天然水」春リニューアル・6/5役員中間報告・評価面談）。`packages/shared-schema/fixtures/`（drive/calendar/tasks＝佐倉美咲の観測データ正本）と整合。
4. **few-shot 規約**: 各プロンプトの **✅良い例を1件だけ** system 末尾に few-shot として差し込む（生成系は「形式・踏み込みの参考＝**内容はコピーせず入力に従え**」の注記を必須＝overfit防止）。**❌悪い例は few-shot に入れず** `eval/` の Eval fixture 専用（採点系の合格/不合格の回帰）。**採点系（leader / editor×2 / judge）は常時ON固定**（スコア内訳つき良い例で閾値を校正＝再現性C5.4）、**生成系（owner / author×2 / persona / cover / step1）はフラグで既定ON・dev で外せる**（`PROMPT_FEWSHOT=on/off`・コスト規律 アーキ§11 R7）。例は一度作れば few-shot と eval の両用。**【C5.2＝実配線済（2026-06-07）】** 良い例の few-shot 注入は `loader.py`／`render.py`、悪い例側は `loader.py` が `❌` ブロックも抽出し、`scripts/eval_harness.py` の `check_fewshot_eval_alignment()` が「良い例＝合格・悪い例＝不合格・eval_judge は `eval/eval_set.yaml` の帯と整合」を**実LLM無しで決定的に回帰**（採点系4本：leader/editor×2/judge）。例を壊す編集は CI で落ちる。
5. **モデル**: ハイブリッド（IO契約 §9）。判断が重い工程＝Pro／観測寄り＝Flash。
6. **知財**: 著者ペルソナ・著者名・経歴はすべて架空。実在著者は作風参考に留める。
7. **悪い例の役割**: 「一般論・最大公約数・水増し・ペルソナ不在」など**Publishrが避けるべき失敗モード**を具体化し、採点エージェント（リーダー/編集長/judge）が確実に弾けることを示す。

---

## ファイル一覧（パイプライン順）

| ファイル | エージェント | モデル | 出力スキーマ（IO契約） |
|---|---|---|---|
| `step1_reader_analyst.md` | 読者分析 | **Pro** | `ReaderProfile`（3層）§3 |
| `step2_research_subs.md` | 調査サブ×3（読者局面/市場/テーマ知見） | Flash（B/C grounding） | `subReaderContext`/`subMarket`/`subThemeInsight` §4-2c |
| `step2_plan_owner.md` | 企画担当者（立案） | **Pro** | `PlanProposal`（8項目）§4-2b |
| `step2_plan_leader.md` | 企画リーダー（スコアゲート） | **Pro** | `LeaderVerdict`（4観点）§4-2a |
| `step3_casting_editor.md` | キャスティング編集者 | **Pro** | `GeneratedPersonaSet`（5人・2軸）§5-3a |
| `step4_author_preview.md` | 著者（プレビュー執筆） | **Pro** | `BookDraft`（7フィールド）§5-2a |
| `step4_editor_preview.md` | 編集長（プレビュー採点） | **Pro** | `EditorVerdict`（プレビュー3観点）§5-2b |
| `step5_cover.md` | 装丁（カバー方針→Imagenプロンプト） | Flash＋Imagen | `coverPrompt`（英語）§6 |
| `modeB_author_body.md` | 著者（本文執筆） | **Pro** | 本文MD §7 |
| `modeB_editor_body.md` | 編集長（本文採点） | **Pro** | 本文ルーブリック5観点 §7 |
| `eval_judge.md` | Eval judge | **Pro** | 企画4観点（リーダーと共通）§8 |

> 移植: 実リポ scaffold 時に本フォルダごと `packages/prompts/` へ。プロンプト本文は文字列定数 or テンプレファイルとして `agents/*.py` から読み込む。
