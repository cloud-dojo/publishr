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

## ファイル一覧（パイプライン順・出版社モデル v4・2026-06-18）

> 「小さな出版社」モデル: 編集長が4サブテーマを決め各チームA/B/C/Dへ割当 → 各チーム（リーダー＋調査3人）が企画書 → 編集長が企画会議でセット承認 → 各リーダーが著者を候補から選抜 → 著者が本文フル執筆 → 担当編集がレビュー → デザイン担当が表紙。詳細は [`agent-io-contract.md`](../../docs/design/agent-io-contract.md)。

| ファイル | エージェント | モデル | 出力スキーマ（IO契約） |
|---|---|---|---|
| `step1_reader_analyst.md` | 読者分析 | **Pro** | `ReaderProfile`（3層）§3 |
| `step2_editor_chief_themes.md` | 編集長（テーマ設定・4テーマ割当） | **Pro** | `ThemeAssignmentSet` §4-0 |
| `step2_research_trend.md` | トレンドリサーチャー（今・時間軸） | Flash grounding | `SubTrendInsight` §4-2c |
| `step2_research_competitors.md` | 競合書籍リサーチャー（市場・競合軸） | Flash grounding | `SubMarket` §4-2c |
| `step2_research_classics.md` | 古典・本質リサーチャー（普遍・不変軸） | Flash grounding | `SubThemeInsight` §4-2c |
| `step2_plan_owner.md` | チームリーダー（企画立案） | **Pro** | `PlanProposal`（8項目＋配本属性）§4-2b |
| `step2_editor_chief_gate.md` | 編集長（企画会議・セットゲート） | **Pro** | `PlanSetVerdict`（per-plan＋portfolio）§4-2a |
| `step3_author_casting.md` | キャスティング（候補生成→1人選抜） | **Pro** | `AuthorCasting`（候補＋chosen＋理由）§5-3a |
| `step4_author_preview.md` | 著者（棚カード＋章アウトライン） | **Pro** | `BookDraft`（7フィールド）§5-2a |
| `step4_editor_preview.md` | 担当編集（棚カード採点） | **Pro** | `EditorVerdict`（プレビュー3観点）§5-2b |
| `modeB_author_body.md` | 著者（本文フル執筆・Mermaid図解） | **Pro** | 本文MD（{{body_volume}}・既定1万〜2万字）§7 |
| `modeB_editor_body.md` | 担当編集（本文採点） | **Pro** | 本文ルーブリック5観点 §7 |
| `step5_cover.md` | デザイン担当（カバー方針→Imagenプロンプト） | Flash＋Imagen | `coverPrompt`（英語）§6 |
| `eval_judge.md` | Eval judge | **Pro** | 企画4観点（per-planと共通）§8 |

### 旧ファイル（後継へ移行・registry配線切替まで併存）
| 旧ファイル | 後継 |
|---|---|
| `step2_editorial_intent.md` | → `step2_editor_chief_themes.md`（テーマ割当を統合） |
| `step2_research_subs.md`（読者局面/市場/テーマ知見） | → `step2_research_trend` / `step2_research_competitors` / `step2_research_classics`（読者局面はSTEP1共有へ） |
| `step2_plan_leader.md` | → `step2_editor_chief_gate.md`（per-plan＋portfolioのセット採点へ拡張） |
| `step3_casting_editor.md` | → `step3_author_casting.md`（候補→選抜＋理由） |

> registry/state_keys/orchestration の配線切替（PR-4以降）で旧ファイルは廃止。dangling だった `step2_serendipity_themes`（registry参照・実ファイル無）はセレンディピティ別ロジックの実装フェーズで新設する。
