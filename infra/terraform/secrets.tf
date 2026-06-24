# ───────────────────────── Secret Manager（C4.1 OAuth / Langfuse）─────────────────────────
# 「箱」(secret container) のみ terraform 管理。秘密の値（version）はコードに置かず、
# apply 後に手動投入する（git に秘密を残さない）:
#   echo -n "<値>" | gcloud secrets versions add <NAME> --data-file=- --project=publishr-498123
# Cloud Run はこれらを env の secret_key_ref（main.tf）で version=latest 参照する。
# 別プロジェクトに新規構築する場合は、apply 後に各 secret へ値を投入してから BFF を起動する。

locals {
  # BFF が参照する secret 名（= secret_id）。全て automatic replication。
  bff_secrets = toset([
    "GOOGLE_OAUTH_CLIENT_SECRET",  # OAuth クライアントシークレット
    "PUBLISHR_OAUTH_STATE_SECRET", # OAuth state（CSRF/uid 紐付け）の HMAC 署名鍵
    "LANGFUSE_HOST",               # Langfuse トレーシング接続先
    "LANGFUSE_PUBLIC_KEY",         # Langfuse 公開鍵
    "LANGFUSE_SECRET_KEY",         # Langfuse 秘密鍵
  ])
}

resource "google_secret_manager_secret" "bff" {
  for_each  = local.bff_secrets
  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
