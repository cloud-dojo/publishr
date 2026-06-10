variable "project_id" {
  type        = string
  description = "GCP プロジェクト ID。"
  default     = "publishr-498123"
}

variable "project_number" {
  type        = string
  description = "GCP プロジェクト番号。Cloud Run の *.run.app URL と Pub/Sub サービスエージェントの導出に使う。"
  default     = "355143691286"
}

variable "region" {
  type        = string
  description = "主要リージョン（Cloud Run / Scheduler / Artifact Registry / Firestore）。"
  default     = "asia-northeast1"
}

variable "service_name" {
  type        = string
  description = "Cloud Run サービス名。*.run.app URL の組み立てにも使う。"
  default     = "publishr-api"
}

variable "image" {
  type        = string
  description = <<-EOT
    Cloud Run コンテナイメージ。通常は `gcloud run deploy --source` か CI(B3.2) が更新する。
    terraform は image 変更を ignore_changes するため、ここはブートストラップ時の初期値。
  EOT
  default     = "asia-northeast1-docker.pkg.dev/publishr-498123/cloud-run-source-deploy/publishr-api:latest"
}

variable "demo_uid" {
  type        = string
  description = "トークン未検証時のフォールバック owner（デモ垢＝佐倉 美咲 / publishr.hackathon）。C4.9 で本番はトークン由来に置換予定。"
  default     = "5JLLGOc3rpXiGN9KXmsISBNAKty2"
}

variable "pubsub_topic" {
  type        = string
  description = "執筆ジョブ用 Pub/Sub トピック名。"
  default     = "publishr-writing"
}

variable "max_books_per_run" {
  type        = string
  description = "1回の自律入荷で予約する最大冊数（C2.1 予約上限）。"
  default     = "5"
}

variable "honmei_schedule" {
  type        = string
  description = "本命テーマの自律入荷 cron（水・土 06:00 JST）。"
  default     = "0 6 * * 3,6"
}
