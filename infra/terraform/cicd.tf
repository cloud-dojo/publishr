# B3.2 CI/CD: GitHub Actions → Cloud Run（WIF keyless 認証・鍵JSON不要）。
# main マージで .github/workflows/ci.yml の deploy ジョブが `gcloud run deploy --source` を実行する。

resource "google_service_account" "ci_deployer" {
  account_id   = "publishr-ci-deployer"
  display_name = "Publishr CI deployer (GitHub Actions -> Cloud Run)"
}

# gcloud run deploy --source（Cloud Build でビルド→Artifact Registry→Cloud Run）に必要な最小ロール
resource "google_project_iam_member" "ci_deployer_roles" {
  for_each = toset([
    "roles/run.admin",               # サービス更新
    "roles/cloudbuild.editor",       # ソースからのビルド起動
    "roles/artifactregistry.writer", # イメージ push
    "roles/storage.admin",           # ソースアップロード
    "roles/iam.serviceAccountUser",  # runner / cloudbuild SA を actAs
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.ci_deployer.email}"
}

# GitHub Actions OIDC を受ける Workload Identity プール／プロバイダ
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }
  # cloud-dojo 組織のリポジトリからのトークンのみ受理
  attribute_condition = "assertion.repository_owner == 'cloud-dojo'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# cloud-dojo/publishr リポジトリのみ deployer SA を借用できる（最小権限）
resource "google_service_account_iam_member" "ci_deployer_wif" {
  service_account_id = google_service_account.ci_deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/cloud-dojo/publishr"
}
