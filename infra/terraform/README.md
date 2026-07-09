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

### C. Discord アラート中継の有効化（本文未承認published）

`monitoring.tf` の alert policy → `google_monitoring_notification_channel.discord` → publishr-api の
`/api/monitoring/discord-alert` → Discord へ転送する。Discord webhook URL は Secret Manager に**手動投入**する
（git/state/plan に出さない）。Cloud Run の `secret_key_ref version=latest` は版が無いと revision 起動に失敗するため、
**箱を作る → 値を投入 → 本 apply** の順で行う:

```bash
cd infra/terraform
# 1) secret の箱だけ先に作る（URL 用。既存 secret は no-op）
terraform apply -target=google_secret_manager_secret.bff
# 2) Discord webhook URL を投入（Discord 側で Reset 発行した新URL・チャットや git には出さない）
printf '%s' '<Discord webhook URL>' | \
  gcloud secrets versions add PUBLISHR_DISCORD_ALERT_WEBHOOK_URL --data-file=- --project=publishr-498123
# 3) 本 apply（通知チャネル・保護トークン・Cloud Run env を反映）
terraform apply
```

中継トークン（`PUBLISHR_MONITORING_WEBHOOK_TOKEN`）は `random_password` で版まで terraform が生成するので手動投入不要。
endpoint は `?token=` 不一致を 401 で弾き、`PUBLISHR_DISCORD_ALERT_WEBHOOK_URL` 未設定なら no-op（ローカル/mock は無効）。
中継 endpoint を含むイメージがデプロイ済みであること（`gcloud run deploy --source` / CI）。

## 設計メモ

- **URL 自己参照回避**: `PUBSUB_PUSH_AUDIENCE` 等は Cloud Run の自 URL を必要とするが、リソース定義内での自己参照は循環するため `locals.base_url`（project-number 形式）で決定的に組み立てている。
- **mock 既定の徹底**: `PUBLISHR_LLM=mock`／`DATA_SOURCE=firestore`。実 LLM/Imagen（課金）は env を手動で `vertex` に上げたときだけ。CLAUDE.md のコスト規律に従う。
- **冪等性 I-20**: push sub は `retry_policy` でリトライ。二重配信はワーカー側の冪等ガード（`process_write_job`：writeable 状態でなければ skip）で吸収する前提。
- **セキュリティ（C4.9 で強化予定）**: 現状 Cloud Run は `allUsers` invoker（web 直叩きのため）。push/trigger は OIDC で別途保護。本番は「トークン由来 owner・allowlist・fail-closed」を C4.9 で入れる。
- **env ドリフトの明文化（7/2）**: デモ公開のライブ生成ガード（`PUBLISHR_DEMO_RATE_GLOBAL_CAP=7`／`PUBLISHR_DEMO_RATE_PER_CLIENT_CAP=3`／`PUBLISHR_SET_MAX_BOOKS=1`）は live に gcloud で直接投入されていて main.tf に無かった＝**任意の `terraform apply` がこれらを剥がす**状態だった。Discord 中継 PR で main.tf に取り込み、apply が誤って消さないようにした。Cloud Run の env は terraform を正本にする（今後の live 直変更は必ず .tf にも反映）。
