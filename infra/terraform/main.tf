locals {
  # Cloud Run の project-number URL（自己参照を避けるため決定的に組み立てる）
  base_url        = "https://${var.service_name}-${var.project_number}.${var.region}.run.app"
  worker_url      = "${local.base_url}/api/worker/write"     # Pub/Sub push 先（執筆ワーカー）
  plan_worker_url = "${local.base_url}/api/worker/plan"      # Pub/Sub push 先（企画ワーカー・C2非同期）
  trigger_url     = "${local.base_url}/api/trigger/planning" # Scheduler 起動先（自律入荷）
  # Pub/Sub サービスエージェント（push 用 OIDC トークン生成に tokenCreator が要る）
  pubsub_agent = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# ───────────────────────── APIs ─────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "cloudscheduler.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "iam.googleapis.com",
    "sts.googleapis.com",            # WIF（B3.2 CI/CD 認証）
    "iamcredentials.googleapis.com", # WIF トークン発行
  ])
  service            = each.value
  disable_on_destroy = false
}

# ───────────────────────── Service Accounts ─────────────────────────
# BFF/ワーカーの実行 SA（Firestore 読み書き・Pub/Sub 発行・Vertex/Imagen）
resource "google_service_account" "runner" {
  account_id   = "publishr-runner"
  display_name = "publishr-runner"
  description  = "Publishr Cloud Run SA"
}

# Pub/Sub push と Cloud Scheduler が Cloud Run を OIDC で叩くための SA
resource "google_service_account" "pubsub_push" {
  account_id   = "publishr-pubsub-push"
  display_name = "Pub/Sub push invoker"
}

# ───────────────────────── Artifact Registry ─────────────────────────
# gcloud run deploy --source / Cloud Build が push する Docker リポジトリ
resource "google_artifact_registry_repository" "cloud_run_source" {
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  format        = "DOCKER"
  description   = "Cloud Run Source Deployments"
  depends_on    = [google_project_service.apis]
}

# ───────────────────────── Cloud Run (BFF + worker) ─────────────────────────
resource "google_cloud_run_v2_service" "api" {
  name                = var.service_name
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runner.email
    timeout         = "3600s"

    scaling {
      max_instance_count = 3
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      # 切替シーム: firestore + LLM。live は実 Vertex（PUBLISHR_LLM=vertex・課金）。
      env {
        name  = "DATA_SOURCE"
        value = "firestore"
      }
      env {
        name  = "PUBLISHR_LLM"
        value = "vertex"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "DEMO_UID"
        value = var.demo_uid
      }
      env {
        name  = "PUBLISHR_MAX_BOOKS_PER_RUN"
        value = var.max_books_per_run
      }
      # 執筆キュー: pubsub（②実Cloud Pub/Sub）。ローカルは mock。
      env {
        name  = "QUEUE"
        value = "pubsub"
      }
      env {
        name  = "PUBSUB_TOPIC"
        value = var.pubsub_topic
      }
      # push ワーカーの OIDC 検証（audience＝自分の /api/worker/write・送信元 SA）
      env {
        name  = "PUBSUB_PUSH_AUDIENCE"
        value = local.worker_url
      }
      env {
        name  = "PUBSUB_PUSH_SA"
        value = google_service_account.pubsub_push.email
      }
      # 手動トリガー（POST /api/trigger/planning）のサーバ側ロック（実 Vertex 企画＝課金）。
      # 空 = 全許可(dev)。本番はデモの佐倉 uid のみ許可し、非許可 uid は 403（routers/api.py の
      # TriggerGuard）。フロントの NEXT_PUBLIC_TRIGGER_UIDS（apphosting.yaml）と対で多層防御。
      # pydantic の list[str]＝JSON 配列文字列で渡す（jsonencode で ["uid",...] を生成）。
      env {
        name  = "ALLOWED_TRIGGER_UIDS"
        value = jsonencode(var.allowed_trigger_uids)
      }

      # ── 以下は live（gcloud 運用更新）の実態に整合させた env。terraform を実態の正本に
      #    するため describe をそのまま反映（plan ゼロ）。値変更は本コードか gcloud で。──
      # 観測ソース＝実 Google / 予約=実執筆は認証必須（fail-closed）。
      env {
        name  = "PUBLISHR_OBSERVE"
        value = "google"
      }
      env {
        name  = "PUBLISHR_REQUIRE_RESERVE_AUTH"
        value = "1"
      }
      # モードB本文＝GCS オフロード（C3.3）。
      env {
        name  = "PUBLISHR_BODY_STORE"
        value = "gcs"
      }
      env {
        name  = "PUBLISHR_BODY_BUCKET"
        value = "publishr-contents-498123"
      }
      env {
        name  = "PUBLISHR_COVER_BUCKET"
        value = "publishr-contents-498123"
      }
      env {
        name  = "PUBLISHR_BODY_CHARS_PER_CHAPTER"
        value = "1500"
      }
      env {
        name  = "PUBLISHR_BODY_MAX_CHAPTERS"
        value = "3"
      }
      env {
        name  = "PUBLISHR_BODY_EDIT_ROUNDS"
        value = "1"
      }
      # 表紙 Imagen ＋ Vertex 経由（us-central1）。
      env {
        name  = "ENABLE_IMAGEN"
        value = "true"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "us-central1"
      }
      # 企画(モードA)非同期 worker の push audience（C2）。
      env {
        name  = "PUBSUB_PLAN_PUSH_AUDIENCE"
        value = local.plan_worker_url
      }
      # OAuth(C4.1) 連携。client_id は公開値、戻り先 URL は live のサービス URL。
      env {
        name  = "PUBLISHR_WEB_APP_URL"
        value = "https://publishr--publishr-498123.asia-east1.hosted.app"
      }
      env {
        name  = "PUBLISHR_OAUTH_REDIRECT_URI"
        value = "https://publishr-api-24ru3hr7fq-an.a.run.app/api/auth/google/callback"
      }
      env {
        name  = "PUBLISHR_OAUTH_TOKEN_STORE"
        value = "secret_manager"
      }
      env {
        name  = "PUBLISHR_SECRET_MANAGER_PROJECT"
        value = "publishr-498123"
      }
      env {
        name  = "GOOGLE_OAUTH_CLIENT_ID"
        value = "355143691286-cv63k6bouj2plhgs93qkkas3b9t6ndd7.apps.googleusercontent.com"
      }

      # ── 秘密は値を持たず Secret Manager 参照（terraform は箱を作らず参照のみ。
      #    箱と値は別管理＝git に秘密を置かない）。──
      env {
        name = "GOOGLE_OAUTH_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "GOOGLE_OAUTH_CLIENT_SECRET"
            version = "latest"
          }
        }
      }
      env {
        name = "PUBLISHR_OAUTH_STATE_SECRET"
        value_source {
          secret_key_ref {
            secret  = "PUBLISHR_OAUTH_STATE_SECRET"
            version = "latest"
          }
        }
      }
      env {
        name = "LANGFUSE_HOST"
        value_source {
          secret_key_ref {
            secret  = "LANGFUSE_HOST"
            version = "latest"
          }
        }
      }
      env {
        name = "LANGFUSE_PUBLIC_KEY"
        value_source {
          secret_key_ref {
            secret  = "LANGFUSE_PUBLIC_KEY"
            version = "latest"
          }
        }
      }
      env {
        name = "LANGFUSE_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = "LANGFUSE_SECRET_KEY"
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis]

  lifecycle {
    # イメージは gcloud run deploy --source / CI(B3.2) が更新するため terraform 管理外。
    # build_config は --source デプロイの一時成果物（ビルドID/ソースzip URL・毎回変わる）。
    # サービスレベル scaling は API が既定値（min/manual=0）を自動補完するため無視。
    ignore_changes = [
      template[0].containers[0].image,
      build_config,
      scaling,
      client,
      client_version,
    ]
  }
}

# 公開エンドポイント（web/ブラウザから直接叩く）。
# ※ C4.9 で「トークン由来 owner・allowlist」を入れるまでの暫定。push/trigger は OIDC で別途保護。
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ───────────────────────── Pub/Sub (執筆キュー) ─────────────────────────
resource "google_pubsub_topic" "writing" {
  name       = var.pubsub_topic
  depends_on = [google_project_service.apis]
}

# push サブスクリプション → Cloud Run /api/worker/write（OIDC 付き）
resource "google_pubsub_subscription" "writing_push" {
  name  = "${var.pubsub_topic}-push"
  topic = google_pubsub_topic.writing.id
  # live は ack 600（執筆は実 Vertex で長め・gcloud 運用更新で 120→600 済）。retry_policy は
  # live に未設定（既定リトライ）＝実態に合わせて宣言しない。冪等ガード I-20 が前提。
  ack_deadline_seconds = 600

  push_config {
    push_endpoint = local.worker_url
    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.worker_url
    }
  }
}

# ── 企画(モードA)非同期キュー（C2）。重い実Vertex企画を /trigger/planning から切り離す ──
#
# ⚠️ これらは 2026-06-15 に **gcloud で本番作成済**（topic publishr-planning / subscription
#    publishr-planning-push / runner publisher）。state を持つ環境で次の import を実行してから
#    apply すること（import 無しで apply すると "already exists" で失敗する）:
#
#      terraform import google_pubsub_topic.planning \
#        projects/publishr-498123/topics/publishr-planning
#      terraform import google_pubsub_subscription.planning_push \
#        projects/publishr-498123/subscriptions/publishr-planning-push
#      terraform import google_pubsub_topic_iam_member.runner_publisher_planning \
#        "projects/publishr-498123/topics/publishr-planning roles/pubsub.publisher serviceAccount:publishr-runner@publishr-498123.iam.gserviceaccount.com"
#
# ⚠️ さらに本 state は本セッションの多数の gcloud 変更（Cloud Run env: PUBSUB_PLAN_PUSH_AUDIENCE/
#    PUBLISHR_OBSERVE/PUBLISHR_BODY_STORE/OAuth secret 参照 等、IAM: secretmanager カスタムロール、
#    writing サブスクの ack_deadline 600 など）と広くドリフトしている。`terraform apply` 前に
#    `terraform plan` 差分を必ず確認し、env/IAM の巻き戻しが起きないよう main.tf を実態に合わせて
#    更新すること（本PRは planning 資源の追加のみ。Cloud Run env ブロックは意図的に未変更）。
resource "google_pubsub_topic" "planning" {
  name       = var.pubsub_planning_topic
  depends_on = [google_project_service.apis]
}

# push サブスクリプション → Cloud Run /api/worker/plan（OIDC 付き）。
# 企画は実Vertex で数分かかるため ack_deadline は長め（600s）。worker は失敗時も 2xx で ack するので
# 再配信は genuine な push 失敗時のみ（10〜60s backoff）。
resource "google_pubsub_subscription" "planning_push" {
  name                 = "${var.pubsub_planning_topic}-push"
  topic                = google_pubsub_topic.planning.id
  ack_deadline_seconds = 600

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "60s"
  }

  push_config {
    push_endpoint = local.plan_worker_url
    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.plan_worker_url
    }
  }
}

# ───────────────────────── Cloud Scheduler (自律入荷) ─────────────────────────
# 本命テーマ＝水/土 06:00 JST に Cloud Run トリガーを OIDC で叩く（C1.7）。
resource "google_cloud_scheduler_job" "honmei" {
  name             = "publishr-honmei"
  region           = var.region
  schedule         = var.honmei_schedule
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "300s"
  depends_on       = [google_project_service.apis]

  # live が保持する既定 retry（Cloud Scheduler のデフォルト値）を明示＝plan ゼロ。
  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    uri         = local.trigger_url
    http_method = "POST"
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode(jsonencode({ userId = "u_sakura" }))
    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.trigger_url
    }
  }
}

# セレンディピティ＝日 06:00 JST。themeKind は API→worker→mode_a まで貫通済み（7f6ddae）なので有効化（C1.7）。
# body の themeKind=serendipity が editor_chief_themes の serendipity 分岐を駆動する。
resource "google_cloud_scheduler_job" "serendipity" {
  name             = "publishr-serendipity"
  region           = var.region
  schedule         = "0 6 * * 0"
  time_zone        = "Asia/Tokyo"
  attempt_deadline = "180s"
  depends_on       = [google_project_service.apis]

  # live が保持する既定 retry（Cloud Scheduler のデフォルト値）を明示＝plan ゼロ。
  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    uri         = local.trigger_url
    http_method = "POST"
    headers = {
      "Content-Type" = "application/json"
    }
    # live の実 body（gcloud 設定時の挿入順＋先頭空白）をそのまま固定＝plan ゼロ。
    # 復号: ` {"userId":"u_sakura","themeKind":"serendipity"}`（jsonencode はキー順が変わり一致しない）。
    body = "IHsidXNlcklkIjoidV9zYWt1cmEiLCJ0aGVtZUtpbmQiOiJzZXJlbmRpcGl0eSJ9"
    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.trigger_url
    }
  }
}

# ───────────────────────── IAM ─────────────────────────
# runner: Firestore 読み書き（実態は datastore.editor＝import 時のライブ値に整合）
resource "google_project_iam_member" "runner_datastore" {
  project = var.project_id
  role    = "roles/datastore.editor"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

# runner: 予約時に Pub/Sub へ発行
resource "google_pubsub_topic_iam_member" "runner_publisher" {
  topic  = google_pubsub_topic.writing.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.runner.email}"
}

# runner: 企画トリガー時に企画トピックへ発行（C2 非同期企画）
resource "google_pubsub_topic_iam_member" "runner_publisher_planning" {
  topic  = google_pubsub_topic.planning.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.runner.email}"
}

# runner: Vertex/Imagen（PUBLISHR_LLM=vertex 時のみ実行使用）
resource "google_project_iam_member" "runner_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

# push SA: Cloud Run を呼べる（Pub/Sub push と Scheduler の両方がこの SA を使う）
resource "google_cloud_run_v2_service_iam_member" "push_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_push.email}"
}

# Pub/Sub サービスエージェント: push 用 OIDC トークンを push SA として発行できる
resource "google_service_account_iam_member" "pubsub_agent_token_creator" {
  service_account_id = google_service_account.pubsub_push.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.pubsub_agent
}
