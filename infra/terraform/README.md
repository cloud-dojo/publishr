# Publishr インフラ IaC（B4.1）

ハッカソンで手作業（gcloud）構築した本番寄りインフラを Terraform で正本化する。
**「再現可能なリポジトリ」**（提出ゴール）を満たすため、`terraform apply` 一発で別プロジェクトに同じ構成を再現できる状態を目指す。

## 対象リソース

| 種別 | リソース | 役割 |
|---|---|---|
| Cloud Run | `publishr-api` | BFF＋執筆ワーカー（`/api/worker/write`）＋自律トリガー（`/api/trigger/planning`） |
| Pub/Sub | topic `publishr-writing` ＋ push sub `publishr-writing-push` | 予約→執筆ジョブ。push は OIDC で Cloud Run を叩く |
| Cloud Scheduler | `publishr-honmei`（水/土 06:00 JST）／`publishr-serendipity`（日 06:00 JST・`themeKind=serendipity`） | 自律入荷（C1.7）。OIDC で trigger を叩く |
| Service Account | `publishr-runner` / `publishr-pubsub-push` | 実行用 / push・scheduler invoker |
| Artifact Registry | `cloud-run-source-deploy` | `gcloud run deploy --source` の push 先 |
| IAM | datastore.user・pubsub.publisher・aiplatform.user・run.invoker・tokenCreator | 上記を結ぶ最小権限 |

### 対象外（別ツール管理）

- **Firestore DB / セキュリティルール / インデックス** … `firebase deploy`（`firebase.json` / `firestore.indexes.json`・C3.1）。
- **Web（App Hosting）** … Firebase App Hosting（`apphosting.yaml`・main push で自動再ビルド・B3.3）。
- **コンテナイメージ** … `gcloud run deploy --source` か CI（B3.2）。terraform は image を `ignore_changes`。
- **OAuth クライアント / シークレット** … `.secrets/`（コミット禁止）。

## 使い方

> ⚠️ ローカルにこのリポジトリを clone した環境には terraform 未インストール。`terraform` が入ったマシン / CI で実行する。

### A. まっさらな別プロジェクトに再現

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # project_id / project_number を編集
terraform init
terraform plan
terraform apply
# 出力された service_url に対し、別途イメージをデプロイ:
#   gcloud run deploy publishr-api --source . --region asia-northeast1
```

### B. 既存の publishr-498123 を terraform 管理下に取り込む（import）

現環境のリソースは gcloud で先に作成済み。二重作成を避けるため `terraform import` してから `plan` で差分ゼロを確認する。

```bash
cd infra/terraform
terraform init
P=publishr-498123 ; R=asia-northeast1

terraform import google_service_account.runner       projects/$P/serviceAccounts/publishr-runner@$P.iam.gserviceaccount.com
terraform import google_service_account.pubsub_push  projects/$P/serviceAccounts/publishr-pubsub-push@$P.iam.gserviceaccount.com
terraform import google_artifact_registry_repository.cloud_run_source  projects/$P/locations/$R/repositories/cloud-run-source-deploy
terraform import google_cloud_run_v2_service.api      projects/$P/locations/$R/services/publishr-api
terraform import google_pubsub_topic.writing          projects/$P/topics/publishr-writing
terraform import google_pubsub_subscription.writing_push  projects/$P/subscriptions/publishr-writing-push
terraform import google_cloud_scheduler_job.honmei    projects/$P/locations/$R/jobs/publishr-honmei
# APIs / IAM メンバーも同様に import（google_project_service.apis["run.googleapis.com"] など）

terraform plan   # ← no changes になるよう .tf を実態に合わせる
```

import で差分が出たら **実態に合わせて .tf を直す**（terraform を正とせず、まず一致させる）。差分ゼロにできたら以後は terraform を正本にする。

## 設計メモ

- **URL 自己参照回避**: `PUBSUB_PUSH_AUDIENCE` 等は Cloud Run の自 URL を必要とするが、リソース定義内での自己参照は循環するため `locals.base_url`（project-number 形式）で決定的に組み立てている。
- **mock 既定の徹底**: `PUBLISHR_LLM=mock`／`DATA_SOURCE=firestore`。実 LLM/Imagen（課金）は env を手動で `vertex` に上げたときだけ。CLAUDE.md のコスト規律に従う。
- **冪等性 I-20**: push sub は `retry_policy` でリトライ。二重配信はワーカー側の冪等ガード（`process_write_job`：writeable 状態でなければ skip）で吸収する前提。
- **セキュリティ（C4.9 で強化予定）**: 現状 Cloud Run は `allUsers` invoker（web 直叩きのため）。push/trigger は OIDC で別途保護。本番は「トークン由来 owner・allowlist・fail-closed」を C4.9 で入れる。
