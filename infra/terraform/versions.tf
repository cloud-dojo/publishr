# Publishr インフラ IaC（B4.1）— Terraform / Google provider 定義。
# 対象: Cloud Run(BFF) / Pub-Sub(執筆ワーカー) / Cloud Scheduler(自律入荷) / SA / IAM / Artifact Registry。
# Firestore DB・セキュリティルール・App Hosting は firebase ツール側で管理（C3.1/B3.3）＝本書の対象外。

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
