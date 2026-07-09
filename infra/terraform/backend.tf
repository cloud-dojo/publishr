# Terraform state のリモート保存先（GCS backend）。
# - state には機微情報が混ざりうるため git には置かず、この非公開バケットで一元管理する。
# - versioning 有効＝state 履歴を保持（誤更新からの復旧用）。
# - 認証は application-default credentials（ADC・quota_project=publishr-498123）。
# バケットは terraform 管理外（chicken-and-egg 回避のため gcloud で先行作成済）:
#   gs://publishr-498123-tfstate (asia-northeast1 / uniform access / versioning)
terraform {
  backend "gcs" {
    bucket = "publishr-498123-tfstate"
    prefix = "publishr/infra"
  }
}
