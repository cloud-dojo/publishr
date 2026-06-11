locals {
  # Cloud Run の project-number URL（自己参照を避けるため決定的に組み立てる）
  base_url    = "https://${var.service_name}-${var.project_number}.${var.region}.run.app"
  worker_url  = "${local.base_url}/api/worker/write"      # Pub/Sub push 先（執筆ワーカー）
  trigger_url = "${local.base_url}/api/trigger/planning"  # Scheduler 起動先（自律入荷）
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
  display_name = "Publishr Cloud Run runtime"
}

# Pub/Sub push と Cloud Scheduler が Cloud Run を OIDC で叩くための SA
resource "google_service_account" "pubsub_push" {
  account_id   = "publishr-pubsub-push"
  display_name = "Publishr Pub/Sub push & Scheduler invoker"
}

# ───────────────────────── Artifact Registry ─────────────────────────
# gcloud run deploy --source / Cloud Build が push する Docker リポジトリ
resource "google_artifact_registry_repository" "cloud_run_source" {
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  format        = "DOCKER"
  description   = "Cloud Run source deploy images"
  depends_on    = [google_project_service.apis]
}

# ───────────────────────── Cloud Run (BFF + worker) ─────────────────────────
resource "google_cloud_run_v2_service" "api" {
  name                = var.service_name
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runner.email
    timeout         = "300s"

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
      }

      # 切替シーム: firestore + mock LLM（既定＝決定的・課金ゼロ）。
      # 実 LLM/Imagen を回す場合のみ PUBLISHR_LLM=vertex に手動更新（課金ゲート）。
      env {
        name  = "DATA_SOURCE"
        value = "firestore"
      }
      env {
        name  = "PUBLISHR_LLM"
        value = "mock"
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
    }
  }

  depends_on = [google_project_service.apis]

  lifecycle {
    # イメージは gcloud run deploy --source / CI(B3.2) が更新するため terraform 管理外。
    ignore_changes = [
      template[0].containers[0].image,
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
  name                 = "${var.pubsub_topic}-push"
  topic                = google_pubsub_topic.writing.id
  ack_deadline_seconds = 120

  # 一過性の失敗はリトライ、毒メッセージは指数バックオフで沈める（冪等ガード I-20 が前提）
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  push_config {
    push_endpoint = local.worker_url
    oidc_token {
      service_account_email = google_service_account.pubsub_push.email
      audience              = local.worker_url
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

# セレンディピティ（日 06:00）は trigger に themeKind param を足してから有効化（C1.7 残）。
# resource "google_cloud_scheduler_job" "serendipity" {
#   name      = "publishr-serendipity"
#   region    = var.region
#   schedule  = "0 6 * * 0"
#   time_zone = "Asia/Tokyo"
#   http_target {
#     uri         = local.trigger_url
#     http_method = "POST"
#     headers     = { "Content-Type" = "application/json" }
#     body        = base64encode(jsonencode({ userId = "u_sakura", themeKind = "serendipity" }))
#     oidc_token {
#       service_account_email = google_service_account.pubsub_push.email
#       audience              = local.trigger_url
#     }
#   }
# }

# ───────────────────────── IAM ─────────────────────────
# runner: Firestore 読み書き
resource "google_project_iam_member" "runner_datastore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

# runner: 予約時に Pub/Sub へ発行
resource "google_pubsub_topic_iam_member" "runner_publisher" {
  topic  = google_pubsub_topic.writing.name
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
