# P1 GCP基盤 実行手順書（Runbook・コマンド一覧）

> **位置づけ**: 全体構築プラン [`docs/planning/docs-replicated-bonbon.md`](../planning/docs-replicated-bonbon.md) の **Phase 1（GCP基盤: 現状確認 → 不足分を構築）** を、コピペ実行できる `gcloud`/`gsutil`/`bq` コマンド列に落としたもの。
> **原則**: docs は「構築済み」と記録するが実態と齟齬がある前提で、**まず STEP A で実在を確認し、STEP B では「無いものだけ」作る**（二重作成・課金事故の防止）。
> **担当**: GCPオーナー（＝鉄田）。コンソール操作・認証情報が要る箇所のみ手作業。
> **実行環境**: WSL2 (Ubuntu) の `gcloud`（Norton の HTTPS 検査回避のため。詳細は `ERRORS.md`）。
> **完了条件（P1 DoD）**: 基盤がレディで、ローカルから ADC 経由で Vertex Gemini が呼べる（STEP D が通る）。Cloud Run/Job・Scheduler・Pub/Sub は **P1では作らない**（P3〜P5）。

⚠️ **このファイルのコマンドは Claude では実行しない**（オーナー認証と課金が伴うため）。ユーザーが端末で実行する。Claude セッションから流したい場合はプロンプトに `! <command>` を付けて実行する。

---

## 0. 変数（最初に1回・シェルに貼る）

```bash
export PROJECT_ID="publishr-498123"
export PROJECT_NUMBER="355143691286"
export REGION="asia-northeast1"          # アプリ / Firestore / GCS
export EVAL_REGION="us-central1"          # Vertex AI Gen AI Evaluation Service（P6）
export BUCKET="publishr-contents-498123"  # 本文保存（非公開）
export RUNNER_SA="publishr-runner@${PROJECT_ID}.iam.gserviceaccount.com"
export CI_SA="publishr-ci-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "${PROJECT_ID}"
gcloud config set account <あなたのGoogleアカウント>   # 必要なら
gcloud auth login                                      # 未ログインなら（ブラウザ）
```

---

## STEP A. 現状確認（read-only・まず全部これを流す）

```bash
# A-1 プロジェクト存在・課金
gcloud projects describe "${PROJECT_ID}"
gcloud billing projects describe "${PROJECT_ID}"        # billingEnabled: true を確認

# A-2 有効化済みAPI（必要9種が出るか）
gcloud services list --enabled \
  --filter="config.name:(aiplatform.googleapis.com OR run.googleapis.com OR cloudbuild.googleapis.com OR firestore.googleapis.com OR storage.googleapis.com OR pubsub.googleapis.com OR cloudscheduler.googleapis.com OR identitytoolkit.googleapis.com OR secretmanager.googleapis.com OR artifactregistry.googleapis.com)" \
  --format="value(config.name)"

# A-3 Firestore データベース（(default)/Native/asia-northeast1 か）
gcloud firestore databases list --format="table(name,type,locationId)"

# A-4 Cloud Storage バケット
gsutil ls -p "${PROJECT_ID}"
gsutil ls -L -b "gs://${BUCKET}" 2>/dev/null | grep -E "Location|Storage class|Public access" || echo "BUCKET MISSING"

# A-5 サービスアカウント
gcloud iam service-accounts list --format="table(email,displayName)"

# A-6 SA に付いたロール（runner / ci-deployer）
gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten="bindings[].members" \
  --filter="bindings.members:(${RUNNER_SA} OR ${CI_SA})" \
  --format="table(bindings.role, bindings.members)"

# A-7 Secret Manager（5本あるか）
gcloud secrets list --format="value(name)"

# A-8 OAuth クライアント（コンソール確認・CLI非対応）
echo "→ コンソールで確認: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"

# A-9 予算アラート
gcloud billing budgets list --billing-account="$(gcloud billing projects describe ${PROJECT_ID} --format='value(billingAccountName)' | sed 's#billingAccounts/##')" 2>/dev/null || echo "budgets: 要コンソール確認"
```

> **判定**: A の各項目で「あるもの／無いもの」を仕分けし、**無いものだけ** STEP B で作る。台帳 `docs/infra/gcp-setup-log.md` と突き合わせて更新する（STEP E）。

---

## STEP B. 不足分のプロビジョニング（無いものだけ実行）

### B-1 API 有効化（冪等・既存でも無害）

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  identitytoolkit.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

### B-2 Firestore（(default)・Native・asia-northeast1）※A-3 で無い時のみ

```bash
gcloud firestore databases create --location="${REGION}" --type=firestore-native
```

### B-3 Cloud Storage バケット（非公開）※A-4 で MISSING の時のみ

```bash
gcloud storage buckets create "gs://${BUCKET}" \
  --location="${REGION}" \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access \
  --public-access-prevention
```

### B-4 サービスアカウント作成 ※A-5 で無い時のみ

```bash
gcloud iam service-accounts create publishr-runner \
  --display-name="Publishr runtime (Cloud Run / Job / Worker)"
gcloud iam service-accounts create publishr-ci-deployer \
  --display-name="Publishr CI deployer (GitHub Actions)"
```

### B-5 IAM ロール付与（冪等）

```bash
# runtime SA = publishr-runner
for ROLE in \
  roles/aiplatform.user \
  roles/run.invoker \
  roles/datastore.user \
  roles/storage.objectAdmin \
  roles/secretmanager.secretAccessor ; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUNNER_SA}" --role="${ROLE}" --condition=None
done

# CI deployer SA = publishr-ci-deployer
for ROLE in \
  roles/run.admin \
  roles/cloudbuild.builds.editor \
  roles/iam.serviceAccountUser \
  roles/artifactregistry.writer \
  roles/storage.admin ; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CI_SA}" --role="${ROLE}" --condition=None
done
```

### B-6 Secret Manager（値は手元の実値に置換・A-7 で不足分のみ）

```bash
# 例: 標準入力から登録（履歴に残さない）。LANGFUSE_HOST は固定値。
printf '%s' 'https://cloud.langfuse.com' | gcloud secrets create LANGFUSE_HOST --data-file=- 2>/dev/null \
  || printf '%s' 'https://cloud.langfuse.com' | gcloud secrets versions add LANGFUSE_HOST --data-file=-

for NAME in LANGFUSE_PUBLIC_KEY LANGFUSE_SECRET_KEY GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET ; do
  echo "→ ${NAME} を登録（プロンプトに値を貼り、最後に Ctrl-D）:"
  gcloud secrets create "${NAME}" --data-file=- 2>/dev/null \
    || gcloud secrets versions add "${NAME}" --data-file=-
done

# runner SA に各シークレットの accessor を付与（プロジェクト全体の secretAccessor を B-5 で付与済みなら不要）
```

> 🔒 **秘密値はコマンド履歴・gitに残さない**（`--data-file=-` で標準入力。`.env`/JSONキーは gitignore 済み）。

### B-7 Firebase（コンソール作業・CLI限定）

```bash
echo "→ Firebase 連携: https://console.firebase.google.com/  （GCPプロジェクト ${PROJECT_ID} を追加 / Blaze プラン）"
echo "→ Authentication > Sign-in method > Google を有効化（プロバイダ）"
# Firebase Web 設定値 (NEXT_PUBLIC_FIREBASE_*) は Firebase コンソール > プロジェクト設定 > マイアプリ から取得し、フロントの .env へ（P4で使用）
```

### B-8 OAuth 同意画面 + Web クライアント（コンソール作業）

```bash
echo "→ APIライブラリで Drive/Calendar/Tasks API を有効化:"
gcloud services enable drive.googleapis.com calendar-json.googleapis.com tasks.googleapis.com
echo "→ OAuth同意画面（外部・本番(未審査)）: https://console.cloud.google.com/auth/overview?project=${PROJECT_ID}"
echo "   スコープ3つ: .../auth/drive.file  .../auth/calendar.readonly  .../auth/tasks.readonly"
echo "→ 認証情報 > OAuthクライアントID(ウェブ)を作成: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
echo "   リダイレクトURIは当面 http://localhost:8080/api/auth/google/callback。backendデプロイ後に本番URIを追記（B1.2）"
echo "   発行された Client ID / Secret は B-6 の Secret Manager に登録"
```

### B-9 予算アラート ¥10,000（50/90/100%）

```bash
BILLING_ACCOUNT="$(gcloud billing projects describe ${PROJECT_ID} --format='value(billingAccountName)' | sed 's#billingAccounts/##')"
gcloud billing budgets create \
  --billing-account="${BILLING_ACCOUNT}" \
  --display-name="Publishr ¥10,000" \
  --budget-amount=10000JPY \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0
# 不可なら: https://console.cloud.google.com/billing/budgets でGUI設定
```

---

## STEP C. ローカル認証（ADC）＋ 環境変数

```bash
# Application Default Credentials（ローカルから Vertex を叩くため）
gcloud auth application-default login
gcloud auth application-default set-quota-project "${PROJECT_ID}"

# リポジトリ .env（backend）に追記（mock既定は維持。Vertex接続はP2で PUBLISHR_LLM=vertex に切替）
cat >> .env <<'EOF'

# ── GCP / Vertex（P1で設定・実LLMはP2で有効化）──
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=publishr-498123
GOOGLE_CLOUD_REGION=asia-northeast1
# Eval(GEAP)用リージョン（P6）
GOOGLE_CLOUD_EVAL_REGION=us-central1
EOF
```

> `.env` は gitignore 済み。`PUBLISHR_LLM` は **mock のまま**（P1では実LLMを本線に入れない）。

---

## STEP D. Vertex Gemini 疎通スモーク（P1のDoD）

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" GOOGLE_CLOUD_LOCATION="${REGION}" \
uv run python - <<'PY'
from google import genai
client = genai.Client()  # 環境変数から Vertex 設定を読む
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="日本語で『疎通OK』とだけ返して。",
)
print("HELLO GEMINI:", resp.text.strip())
PY
```

- ✅ `HELLO GEMINI: 疎通OK` 等が返れば **P1完了**（ADCで Vertex が叩ける）。
- ❌ 失敗時の典型: 権限不足（runner ではなく自分のアカウントに `aiplatform.user` が要る場合あり）／リージョンでのモデル未提供／quota 不足。エラーを STEP E の台帳に記録し、P2前に潰す。

---

## STEP E. インフラ台帳の更新（P1-4）

`docs/infra/gcp-setup-log.md` を**実態に合わせて更新**する。

- STEP A の確認結果（作成済み / 今回作成 / 意図的に後回し）を反映。
- **後回し（P1では作らない）を明記**: Cloud Run サービス / Cloud Run Job（曜日別×3）/ Cloud Scheduler / Pub/Sub `book-writing` / Artifact Registry リポジトリ / Firebase App Hosting backend。
- OAuth 本番リダイレクトURI 追記（B1.2）は backend デプロイ後（P5）であることを注記。

---

## チェックリスト（P1完了判定）

| 項目 | 確認 | 状態 |
|---|---|---|
| 必要9 API 有効 | STEP A-2 / B-1 | ⬜ |
| Firestore (default)/Native/asia-northeast1 | A-3 / B-2 | ⬜ |
| GCS `publishr-contents-498123`（非公開・UBLA） | A-4 / B-3 | ⬜ |
| SA `publishr-runner`＋5ロール | A-5,A-6 / B-4,B-5 | ⬜ |
| SA `publishr-ci-deployer`＋5ロール | A-5,A-6 / B-4,B-5 | ⬜ |
| Secrets 5本（LANGFUSE×3・OAUTH×2） | A-7 / B-6 | ⬜ |
| Firebase 連携・Blaze・Google Auth 有効 | B-7 | ⬜ |
| OAuth 同意画面(本番)＋スコープ3＋Webクライアント | A-8 / B-8 | ⬜ |
| Drive/Calendar/Tasks API 有効 | B-8 | ⬜ |
| 予算 ¥10,000（50/90/100%） | A-9 / B-9 | ⬜ |
| ADC ログイン＋ `.env` GCP変数 | STEP C | ⬜ |
| **Vertex Gemini 疎通スモーク成功** | STEP D | ⬜ |
| 台帳 `gcp-setup-log.md` 更新 | STEP E | ⬜ |

> 全✅で **P1完了 → P2（ADK MiniLoop・実Vertex・H2）** へ。GitHubオーナー操作（App Hosting連携・Cloud Build接続）は P5/P6 で扱い、当面は CI/CD 方式B（Actions→`gcloud builds submit`）でオーナー依存を回避する。
