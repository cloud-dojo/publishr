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

output "body_forced_approve_metric" {
  description = "本文未承認published検知の log-based metric 名（Console確認用）。"
  value       = google_logging_metric.body_forced_approve.name
}

output "body_forced_approve_alert_policy" {
  description = "本文未承認published検知の alert policy 名（Console確認用）。通知先未設定なら Incidents 一覧でのみ確認可能。"
  value       = google_monitoring_alert_policy.body_forced_approve.name
}
