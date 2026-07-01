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
# 対応: log-based metric でこの warning ログを拾い、alert policy で検知する（レベル1＝
# 観測強化のみ・コード変更なし・スキーマ変更なし）。通知先は var.body_forced_approve_notification_channels
# （既定空リスト）＝決まり次第 channel ID を足すだけでよい。

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

  notification_channels = var.body_forced_approve_notification_channels

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
