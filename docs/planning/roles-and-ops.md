# Publishr 役割分担・運用ルール

> 📑 目次は [正本マップ](../README.md)／未決論点は [open-issues.md](open-issues.md)。
> **位置づけ（2026-06-03 スリム化）**: 本書は **「誰が（役割分担）」＋「どう運用するか（運用ルール）」の正**。
> - **作業分解・実装順序(WBS ID)・ゲート・依存・週次・DoD・マイルストーン → [wbs.md](wbs.md) が正**（エージェント実施の単一正本）
> - **着手ゲート（友人MTG議題・環境・残素材） → [kickoff-checklist.md](kickoff-checklist.md) が正**
> - 旧版にあった §W0準備・§W1〜W6 ToDo・§鉄田独立トラックは上記2枚へ移管（二重管理を排除）。
> **担当凡例**: **鉄田・一瀬**=2人で合意 / **一瀬**=友人（エンジニア）/ **鉄田**（Claude Code含む）。WBS([wbs.md](wbs.md))のタスク担当も同じ3名表記に統一。

---

## 0. プロジェクトの制約（毎回ここに戻る）
- **実働5週間**（6/1〜7/10。大会期間2.5ヶ月と混同しない）／体制＝友人1.0＋鉄田0.5〜1.0＝**約1.5〜2名**。
- **線引き3原則**（MVP §7）: ①縦>横（W2のE2E縦通しが全て）②映らないものは作らない ③必然性<動くデモ。
- **撤退はしない＝やりきる**。詰まれば対策（STEP2のみLangGraphへ逃げる等）で乗り切る。

---

## 1. 役割分担（領域×担当・境界）

> 工数の食い合いを解く肝＝**フロントを鉄田がClaude Codeで巻き取り、友人はエージェント＝審査の核に集中**（アーキ §5）。
> **🔑 エージェントの分業原則（一瀬提案で明確化・2026-06-03）**: **プロンプト・人格・判断基準の「設計」＝鉄田**（`packages/prompts`）／**ランタイム実装・Vertex接続・実行基盤＝一瀬**（`agents/*.py`・`apps/api`）。「中身の質」と「動かす」を物理分離する。詳細は [../design/agent-responsibilities.md](../design/agent-responsibilities.md)。

| 領域 | 主担当 | 境界・補足 | WBS（カテゴリ版） |
|---|---|---|---|
| ADKマルチエージェントの**ランタイム実装**（STEP0-5・モードB） | 一瀬 | 基準1の中核。最優先。**プロンプト設計は鉄田** | C1/C2 |
| **エージェントのプロンプト・人格・判断基準の設計**（企画3階層／キャスティング／編集長［プレビュー3観点・本文ルーブリック］／著者／Eval judge） | 鉄田 | ✅ `packages/prompts/` 11本整備済。残＝W1実テスト＆eval兼用 | A3 |
| STEP0観測・OAuth・Picker（サーバ側） | 一瀬 | 選択UIは鉄田と境界調整（G1-13） | C1.1 |
| Cloud Run / Scheduler / Pub/Sub / Firestore / GCS | 一瀬 | 状態機械・自律トリガー・索引・本文保護。**※基盤Firebase部分（Firestore/GCS）の担当は未定＝鉄田が一瀬を補助する可能性あり・後決め（MTG 2026-06-05）** | C3/C1.7 |
| Imagen表紙生成連携（STEP5） | 一瀬 | dev時はモック（コスト） | C1.6 |
| Langfuse計装・CI/CD・Eval ゲート実装・Terraform | 一瀬 | L4の実装 | C5.6/B3/C5.3/B4 |
| API 3本（reserve/OAuth/trigger） | 一瀬 | 境界は `../design/api-contract.md`・予約同時5冊 | C2.1 |
| 共有スキーマ（型の正本・`packages/shared-schema`） | 一瀬 | fixtures（personas等）は鉄田。B7/G1-11 | A5.2 |
| コスト実測・監視（GCP/Langfuse） | 一瀬 | 方針・上限ガード設計は鉄田 | C5.8 |
| 書店フロントUI（全画面・Picker UI含む） | 鉄田 | テンプレ＋Claude Code。`../ui/ui-spec.md` | C4 |
| ユーザー登録フォーム（initialProfile選択肢） | 鉄田 | G1-9。選択肢は鉄田確定 | C4.1/A3.2 |
| お気に入り著者UI・ハイライト・FB（Firestore直書き） | 鉄田 | ルールは `../design/firestore-security-rules.md` | C4.5/C4.6 |
| Eval Set設計・品質ゲート項目 | 鉄田 | ✅8件作成済。CI実装は一瀬 | A4/C5.3 |
| デモ台本・録画・ピッチ図解・README | 鉄田 | 基準2・4の訴求 | C6 |
| テーマ・スコープ管理・コスト概算（方針・ガード） | 鉄田 | 意思決定・予算 | C5.7/C5.8 |
| **Eval品質ゲートの実装（Gen AI Eval Service・GEAP）＝一瀬／ProtoPedia作品ページ作成＝鉄田** | 一瀬・鉄田 | 2026-06-05追記。Eval実装ルート＝`publishr_other/GEAP②_EvalService具体化.md`（設計=鉄田✅・実装=一瀬）／ProtoPedia草案＝`publishr_other/Protopedia提出/` | C5.3/C6.7 |
| **GitHub組織・ビルド連携（App Hosting / Cloud Build↔GitHub）** | 鉄田 | **MTG 2026-06-05決定／✅移管完了**：GitHubを組織アカウント `cloud-dojo` へ移管→鉄田にもオーナー権限を付与（2026-06-05完了）。これにより App Hosting の GitHub App 連携(B3.3)・Cloud Build↔GitHub 接続(方式A・G1-18) は**鉄田が実施**（旧「リポ所有者=一瀬のみ可」の所有者依存は解消） | B3 |

> 担当の「いつ・何待ち・完了条件」は WBS の各WP表（担当列・依存・DoD）を参照。

---

## 2. 運用ルール
- **タスク管理**: チェックリスト§1⑥で1ツール（GitHub Projects/Notion/Todoist）に決め、**WBSのWP/タスクを起票**（二重管理しない）。WBS＝設計図、ツール＝日々の進捗。
- **同期頻度**: 週1の関門チェック（WBSマイルストーンM1〜M6）＋詰まったら即連絡（撤退せず対策）。
- **スコープ変更**: MVP §4 OUT との照合を必須に（「入れる＝何かを捨てる」）。Stretchは W5 余力次第。
- **コスト**: dev/prodフラグをデフォルトdev（本文ページ/Imagen/冊数）。予算アラート50%でLangfuse内訳点検（G1-16）。
- **真実源の分担**: 役割・運用＝本書／作業・スケジュール＝WBS.md／着手ゲート＝着手チェックリスト.md／設計＝設計資料・packages/prompts。

> 役割分担は**友人MTG（2026-06-05）で基本合意・確定**（チェックリスト§1-A②）。残る未定は基盤Firebase部分の担当のみ（鉄田補助の可能性・後決め）。
