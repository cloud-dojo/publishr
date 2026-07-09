# 本文編集ループが未承認のまま published になったケースの検知（7/1レビュー・レベル1対応）。
#
# 背景: agents/publishr_agents/mode_a.py の make_published_books と
# apps/api/publishr_api/services/reservation_service.py の _generate_body は、
# write_body_loop() が forced_approve=True（rounds上限に達しても編集長が最終的にrevise判定の
# ままだった、または機械チェックで読者プロファイル由来の固有名詞が本文に残存していた）を返しても、
# 既存挙動としてそのまま status="published" にする（デモを止めない方針）。この事実は
# logger.warning(...) でCloud Loggingに残るだけで、Firestoreへの永続化・能動通知は無い＝
# 誰かが能動的にログを見に行かない限り気づけない。
#
# 対応: log-based metric でこの warning ログを拾い、alert policy で検知する。能動通知は
# Discord 中継チャネル（末尾）へ送る。追加の通知先が要れば var.body_forced_approve_notification_channels
# に channel ID を足せば併用される。

resource "google_logging_metric" "body_forced_approve" {
  name   = "publishr-body-forced-approve"
  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.service_name}"
    textPayload=~"published with unapproved body"
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_alert_policy" "body_forced_approve" {
  display_name = "Publishr: 本文が未承認のまま published"
  combiner     = "OR"
  severity     = "WARNING"

  conditions {
    display_name = "forced_approve ログが1件以上発生（1時間あたり）"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.body_forced_approve.name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "0s"
      aggregations {
        alignment_period   = "3600s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }

  # Discord 中継チャネル（下記）＋任意の追加チャネル（var）へ通知。
  notification_channels = concat(
    var.body_forced_approve_notification_channels,
    [google_monitoring_notification_channel.discord.id],
  )

  alert_strategy {
    auto_close = "604800s" # 7日で自動クローズ
  }

  documentation {
    content   = <<-EOT
      本文編集ループがrounds上限に達しても未承認のまま（または機械チェックで読者プロファイル
      由来の固有名詞の残存を検出して）published になった本があります。
      Cloud Logging で `published with unapproved body` を検索し、該当する book_id を
      確認してください（score/decision/weakChaptersがログに含まれます）。
    EOT
    mime_type = "text/markdown"
  }

  depends_on = [google_project_service.apis]
}

# ── Discord 中継（7/2）────────────────────────────────────────────────────────
# GCP は Discord webhook を直接叩けない（インシデントJSON形式が Discord の {content|embeds} と
# 非互換）。そこで publishr-api（Cloud Run）に中継 endpoint `/api/monitoring/discord-alert` を置き、
# GCP の webhook 通知チャネルからそこへ POST → Discord 形式へ整形して転送する。
#
# 公開 Cloud Run 上のため、endpoint は URL 埋め込みトークン（?token=）で保護する。トークンは
# terraform 生成のランダム値（値は state のみ・git非公開）で、チャネルURLと Cloud Run 環境変数
# （PUBLISHR_MONITORING_WEBHOOK_TOKEN・main.tf）に同一値を配る。Discord webhook URL 自体は
# Secret Manager（PUBLISHR_DISCORD_ALERT_WEBHOOK_URL・secrets.tf）に手動投入する（git/plan非公開）。

resource "random_password" "monitoring_webhook_token" {
  length  = 40
  special = false # URL クエリに素で載せるため記号は避ける
}

# トークンは Secret Manager 経由で Cloud Run へ渡す（main.tf は secret_key_ref・平文envに sensitive を
# 載せると plan の env 差分が全マスクされ不可読になるのを回避）。値は terraform が版まで作る（手動投入不要）。
resource "google_secret_manager_secret" "monitoring_webhook_token" {
  secret_id = "PUBLISHR_MONITORING_WEBHOOK_TOKEN"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "monitoring_webhook_token" {
  secret      = google_secret_manager_secret.monitoring_webhook_token.id
  secret_data = random_password.monitoring_webhook_token.result
}

resource "google_monitoring_notification_channel" "discord" {
  display_name = "Publishr Discord 中継（本文未承認published）"
  type         = "webhook_tokenauth"

  labels = {
    # publishr-api の中継 endpoint。?token= は endpoint 側で照合（不正 POST を弾く）。
    url = "${google_cloud_run_v2_service.api.uri}/api/monitoring/discord-alert?token=${random_password.monitoring_webhook_token.result}"
  }

  depends_on = [google_project_service.apis]
}
