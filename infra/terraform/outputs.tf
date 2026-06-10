output "service_url" {
  description = "Cloud Run BFF の URL（terraform 管理）。"
  value       = google_cloud_run_v2_service.api.uri
}

output "worker_url" {
  description = "Pub/Sub push 先（執筆ワーカー）。"
  value       = local.worker_url
}

output "trigger_url" {
  description = "Cloud Scheduler 起動先（自律入荷トリガー）。"
  value       = local.trigger_url
}

output "runner_sa" {
  description = "Cloud Run 実行 SA。"
  value       = google_service_account.runner.email
}

output "pubsub_push_sa" {
  description = "Pub/Sub push & Scheduler invoker SA。"
  value       = google_service_account.pubsub_push.email
}

output "writing_topic" {
  description = "執筆ジョブ Pub/Sub トピック。"
  value       = google_pubsub_topic.writing.name
}
