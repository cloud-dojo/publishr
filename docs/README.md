# Publishr ドキュメント正本マップ

> `publishr/docs/` 配下の全ドキュメントの地図。「どの問いはどのファイルか」「各トピックの正本はどれか」を1枚で示す。
> リンクは本書（`docs/` 直下）からの相対パス。

---

## 正本は2つ（どこに何があるか）

| 正本 | 役割 | 中身 |
|---|---|---|
| **GitHub**（`hiroshiichise/publishr`・private） | プロダクト一式の正本 | コード全部 ＋ Markdownの設計/要件/UI/インフラログ。機械fixtureは `packages/shared-schema/fixtures/*.json` |
| **Google Drive** | 非コードの計画・対外資料 | WBS・マスタースケジュール・ToDo、ピッチ資料、demo台本（デモシナリオ/ペルソナ/著者ペルソナ集/サンプル文書）、会議記録 |

**境界ルール（1問で裁く）**: 「**コード/Eval/CIが（自動で）読むか？** → Yes=GitHub / No=Drive」
ローカル `publishr` は GitHub の作業コピー。`git push` で同期する。

**命名規約**: GitHub/ローカル=英語（ディレクトリ小文字・ファイルkebab-case）。Drive=日本語中心。

**GCP基本情報**（`infra/gcp-setup-log.md` より）:
- Project ID: `publishr-498123` / Region: `asia-northeast1`（東京）
- Firestore DB: `(default)` / Bucket: `publishr-contents-498123` / Service Account: `publishr-runner`

---

## リポジトリ構成

```
publishr/
├─ agents/                 ← ADKエージェント実装（Python）★コード
├─ apps/api/               ← バックエンドAPI ★コード
├─ apps/web/               ← 書店UI（Next.js）★コード
├─ packages/prompts/       ← 各エージェントの完成プロンプト＋良い/悪い出力例 ★コード
├─ packages/shared-schema/ ← 共有スキーマ＋fixtures（drive/calendar/tasks/personas等のJSON）★コード/データ
├─ eval/                   ← Eval Set（CI品質ゲート）★コード
├─ scripts/                ← ローカル開発・Evalハーネス ★コード
└─ docs/
   ├─ README.md            ← 本書（正本マップ）
   ├─ design/              ← 設計仕様（10MD）
   ├─ planning/            ← 役割分担/運用・着手チェックリスト・未決論点台帳（※WBSはDrive）
   ├─ infra/               ← CICD設計・GCP環境構築ログ
   └─ ui/                  ← UI仕様書＋mockups/
```

---

## ファイル一覧

### design/（設計仕様・10MD）
| ファイル | 役割 | いつ見るか |
|---|---|---|
| `design/concept-summary.md` | 構想（なぜ／価値／新規性／UX） | テーマの背景・ストーリー確認 |
| `design/mvp-scope.md` | MVPのIN/OUT・DoD・審査基準カバレッジ・Eval設計 | スコープ判断・Eval設計 |
| `design/tech-architecture.md` | 技術アーキ・**データモデル**・スコープ・週次ロードマップ | 実装設計・スキーマ確認 |
| `design/agent-io-contract.md` | 各エージェントのI/O契約・プロンプト骨子・モデル一覧 | エージェント実装 |
| `design/agent-responsibilities.md` | IO契約の要約＋再設計の同期メモ | 構造同期・プロンプト設計着手前 |
| `design/adk-control-flow.md` | ADK制御フロー（エージェント木・編集ループ・state） | エージェント実装 |
| `design/api-contract.md` | フロント⇔バック境界（認証・登録・予約・OAuth・トリガー） | フロント/API実装 |
| `design/firestore-security-rules.md` | Firestoreルール（所有権・直書き範囲） | Firestore実装 |
| `design/cost-estimate.md` | LLM/Imagenコスト概算・上限ガード | 予算管理 |
| `design/langfuse-tracing.md` | トレース設計（企画スコア・編集ループ・grounding） | Observability計装 |

### planning/（実行管理）
| ファイル | 役割 | いつ見るか |
|---|---|---|
| `planning/roles-and-ops.md` | 役割分担の境界・分業原則・運用ルール | 役割確認 |
| `planning/kickoff-checklist.md` | 着手ゲート（MTG・環境・残素材・未決決着） | 着手準備 |
| `planning/open-issues.md` | 未確定/未決論点・MTG議題・決着ログ | MTG前・意思決定時 |
| **WBS（成果物分解・週次・マイルストーン）** | **Drive管理**（Office） | 作業の全体把握・進捗管理 |

### infra/・ui/
| ファイル | 役割 |
|---|---|
| `infra/cicd.md` | CI/CD・Evalゲート・Observability設計 |
| `infra/gcp-setup-log.md` | GCP環境構築の作業ログ・完了状況 |
| `ui/ui-spec.md` | 画面設計（コンポーネント・Firestore購読・遷移フロー） |
| `ui/mockups/` | デザイン素材（8枚） |

### データ・対外資料の所在
| 種別 | 所在 |
|---|---|
| 機械fixture（STEP0観測・Eval Setの実データ） | `packages/shared-schema/fixtures/*.json`（repo内） |
| demo台本（デモシナリオ・ペルソナ・著者ペルソナ集・サンプル文書） | **Drive** |
| ピッチ（原稿・スライド・PDF） | **Drive** |
| WBS・マスタースケジュール・ToDo・会議記録 | **Drive** |
