# Publishr CI/CD・IaC 設計仕様書

> **位置づけ**: GitHub Actions / Cloud Build / Terraform の「何を・なぜ・いつ作るか」を定義した設計仕様。実装ファイル（`.yml` / `.tf`）はW4で作成する。友人MTGで共有し、W1のGitHub設定作業の根拠にする。
> **全体の目次は `../目次.md`。未確定論点は `../計画/未決論点台帳.md`（OPEN_ISSUES）。**

---

## §1. CI/CDパイプライン全体像

```
[ 鉄田 or 友人が main ブランチに push ]
        │
        ▼
[ GitHub Actions ] ←── W4で実装
  Step 1: lint（Python / TypeScript）
  Step 2: Eval Gate（審査基準5・Observability L4の証明）
           ├ eval/eval_set.yaml × Gemini judge（4観点共通ルーブリック・Vertex AI Gen AI Evaluation Service）
           ├ 本命の総合スコア < 70 → ❌ デプロイ停止
           └ 8件中7件パス（87.5%）→ ✅ 通過
        │ pass
        ▼
[ Cloud Build trigger ] ←── W1で接続（友人担当）
  - Docker イメージビルド
  - Artifact Registry push
        │
        ▼
[ Cloud Run deploy ]
  ├ Backend API（FastAPI）
  └ ADK Runner（Cloud Run Job）
        │
        ▼
[ Langfuse ]（クラウドマネージド・無料枠）
  - Eval 結果・トレース・スコア/ラウンド数を自動記録
  - 品質劣化の可視化 ＝ Observability L4
```

### なぜこの構成か（審査基準5への回答）

| 観点 | 構成の意図 |
|---|---|
| 技術選定の妥当性 | Cloud Run のみで完結（GCE不使用）。Langfuse Cloud でマネージドObservability（GKE自前運用は不採用） |
| 拡張性 | Terraform でコア資源を IaC 化。環境追加（staging等）がコード変更のみで可能 |
| 実運用への配慮 | Eval Gate で「プロンプト改変→品質劣化→自動停止」を構造化。人的チェックに依存しない |

---

## §2. GitHub Actions ワークフロー設計（W4で実装）

**ファイル**: `.github/workflows/deploy.yml`（W4で作成）

**トリガー**: `main` ブランチへの push

**ステップ設計**:

```yaml
# ← W4で実際に書く。ここは設計メモ
name: Publishr CI/CD
on:
  push:
    branches: [main]

jobs:
  eval-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Eval Gate
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
          GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GCP_SA_KEY }}
        run: python scripts/eval_harness.py   # Vertex AI Gen AI Evaluation Service（vertexai.evaluation）で8件採点 → 本命<70 / 8件中7件で停止
      - name: Trigger Cloud Build
        # gcloud builds triggers run ... （W4で詳細化）
```

> **②採用メモ（2026-06-05）**: Eval Gate は自作judgeでなく **Vertex AI Gen AI Evaluation Service**（`vertexai.evaluation`・実体＝`scripts/eval_harness.py`）。SA `publishr-runner` に **`roles/aiplatform.user`** を付与。**eval実行リージョン＝`us-central1`**（appの`asia-northeast1`とは別に `vertexai.init(location=...)` で指定）。**ルーブリック／Evalセット8件／ゲート方針（<70・7/8）は不変**＝実装エンジンの差し替えのみ。実装詳細＝`publishr_other/GEAP②_EvalService具体化.md`。

### GitHub Secrets 登録リスト（W1 GitHub作成後に鉄田が設定）

| Secret名 | 値 | 確認先 |
|---|---|---|
| `GCP_PROJECT_ID` | `publishr-498123` | GCP環境構築ログ.md |
| `GCP_SA_KEY` | サービスアカウントJSONキー（Base64） | GCPコンソール > IAM > サービスアカウント |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-xxxx` | Secret Manager（登録済み） |
| `LANGFUSE_SECRET_KEY` | `sk-lf-xxxx` | Secret Manager（登録済み） |
| `GOOGLE_OAUTH_CLIENT_ID` | OAuth クライアントID | GCPコンソール > 認証情報 |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth クライアントシークレット | GCPコンソール > 認証情報 |

---

## §3. Cloud Build 設定（W1で友人が設定）

**友人担当タスク**（GCP環境構築ログ.md「残タスク」より）:
1. GitHub リポジトリ作成（`publishr`・Public）
2. 鉄田を Collaborator に追加
3. GCP コンソール > Cloud Build > トリガー > GitHub接続
4. `main` ブランチ push で自動ビルドのトリガー設定

**ビルド設定ファイル**: `cloudbuild.yaml`（W4で作成）

**デプロイ先**:
- Cloud Run サービス（Backend API / FastAPI）
- Cloud Run Job（ADK Runner × 曜日別3ジョブ）

**サービスアカウント**: `publishr-runner@publishr-498123.iam.gserviceaccount.com`（設定済み）

---

## §4. Terraform 管理範囲（W3-W4で作成）

### 管理する（IaC化する）

| リソース | 理由 |
|---|---|
| Cloud Run サービス（Backend API） | 設定変更が頻繁・環境差異が出やすい |
| Cloud Run Job（ADK Runner × 3ジョブ） | 曜日別ジョブの定義をコード化 |
| Cloud Scheduler（土/水/日トリガー） | cronスケジュールはコード管理が安全 |
| Pub/Sub トピック（`book-writing`） | 書籍予約の非同期実行の核 |
| IAM バインディング（サービスアカウント権限） | 権限の変更履歴をGitで追う |

### 管理しない（手動 or 既設で固定）

| リソース | 理由 |
|---|---|
| Firestore | 既設・Native mode / asia-northeast1。スキーマ変更はコードで管理 |
| Cloud Storage バケット | 既設（`publishr-contents-498123`）。コンテンツは IaC 外 |
| Firebase Auth | コンソール設定で完結 |
| Secret Manager のシークレット値 | 値はコードに含めない（gitignore対象） |
| Langfuse | 外部SaaS（マネージド） |

### ファイル構成（W3-W4で作成）

```
terraform/
  main.tf        # プロバイダ（google）・バックエンド（GCS state管理）
  cloudrun.tf    # Cloud Run サービス・Job 定義
  scheduler.tf   # Cloud Scheduler 3ジョブ（土/水/日・themeKind別）
  pubsub.tf      # Pub/Sub トピック（book-writing）
  iam.tf         # サービスアカウント → Cloud Run / Job / Scheduler 権限
  variables.tf   # project_id / region / 環境変数の変数定義
  outputs.tf     # Cloud Run URL 等の出力
```

---

## §5. Observability L4 の証明（審査員への訴求ポイント）

**ばんくし氏が「なぜ L4 か」を問うた際の回答**:

```
L1: Logging        ← Cloud Run のデフォルトログ（自動）
L2: Metrics        ← Cloud Monitoring（デフォルト）
L3: Tracing        ← Langfuse でエージェントトレースを記録
L4: Continuous Eval ← ★ Eval Gate が CI に組み込まれている
    「プロンプトを変えたらスコアが下がった」を自動検出して停止
```

**Langfuse で可視化できるもの**（何をどのspan/属性で残すかの詳細仕様 → `../設計/Langfuseトレース仕様.md`）:
- 企画リーダーの採点スコア（4観点）とラウンド数
- 差し戻し → 再提出のログ（必然性の証拠）＝**2系統**（企画スコアループ＋編集長⇄著者の編集ループ）
- 調査サブの Google検索 grounding 取得URL・クエリ（外部実データ取得の証跡）
- Eval Set 8件の実行結果（pass / fail 理由）

---

## §6. 週次ロードマップ（CI/CD観点）

| 週 | 作業 | 担当 |
|---|---|---|
| **W1** | GitHubリポジトリ作成・Cloud Build接続・鉄田Collaborator追加 | 友人 |
| **W1** | GitHub Secrets 登録（§2の6項目） | 鉄田 |
| **W2** | 手動デプロイでE2E縦通し確認（CI/CDはまだ手動） | 友人 |
| **W3** | Cloud Scheduler 3ジョブ設定・Pub/Sub動作確認 | 友人 |
| **W4** | GitHub Actions `.yml` 作成・Eval Gate（`scripts/eval_harness.py`・Vertex AI Gen AI Evaluation Service）・Terraform コア資源・自動デプロイ完成 | 友人（実装）＋鉄田（Eval設計） |
| **W5** | CI/CD 安定確認・Langfuse ダッシュボード整備・デモ録画 | 両者 |

---

## §7. 未確定（友人MTGで詰める）

- `cloudbuild.yaml` のビルドステップ詳細（Dockerfile構成）→ W1の後
- Terraform の state バックエンド（GCSバケット名）→ W3着手前に決定
- staging 環境を別 Cloud Run サービスとして持つか → W4で判断（MVP は production のみでよい）
