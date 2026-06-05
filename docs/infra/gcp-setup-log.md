# Publishr GCP環境構築ログ

**作業日**: 2026-06-03  
**作業者**: 鉄田（Claude Codeサポート）

---

## プロジェクト情報

| 項目 | 値 |
|---|---|
| プロジェクト名 | Publishr |
| プロジェクトID | `publishr-498123` |
| プロジェクト番号 | `355143691286` |
| 請求先アカウント | 個人アカウント（既存流用） |

---

## 有効化済みAPI

| API名 | サービス名 |
|---|---|
| Agent Platform API（旧Vertex AI） | `aiplatform.googleapis.com` |
| Cloud Run Admin API | `run.googleapis.com` |
| Cloud Build API | `cloudbuild.googleapis.com` |
| Cloud Firestore API | `firestore.googleapis.com` |
| Cloud Storage API | `storage.googleapis.com` |
| Cloud Pub/Sub API | `pubsub.googleapis.com` |
| Cloud Scheduler API | `cloudscheduler.googleapis.com` |
| Identity Toolkit API | `identitytoolkit.googleapis.com` |
| Secret Manager API | `secretmanager.googleapis.com` |

---

## 作成済みリソース

### Firestoreデータベース
- データベースID: `(default)`
- エディション: Standard Edition
- モード: Native mode
- リージョン: `asia-northeast1`（東京）

### Cloud Storageバケット
- バケット名: `publishr-contents-498123`
- ストレージクラス: Standard
- リージョン: `asia-northeast1`（東京）
- 公開アクセス: 非公開

### サービスアカウント
- 名前: `publishr-runner`
- メール: `publishr-runner@publishr-498123.iam.gserviceaccount.com`
- 付与ロール:
  - Agent Platform ユーザー
  - Cloud Run 起動元
  - Cloud Datastore 編集者
  - Storage オブジェクト管理者
  - Secret Manager のシークレット アクセサー

### Firebase
- プロジェクト: GCPプロジェクト（publishr-498123）に紐づけ済み
- プラン: Blaze
- 認証: Google OAuth 有効化済み

### Secret Manager登録済みシークレット
| シークレット名 | 内容 |
|---|---|
| `LANGFUSE_SECRET_KEY` | LangfuseのSecret Key |
| `LANGFUSE_PUBLIC_KEY` | LangfuseのPublic Key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` |

---

## Langfuse

| 項目 | 値 |
|---|---|
| Organization | Publishr |
| Project | `publishr-prod` |
| プラン | Hobby（無料） |
| APIキー | Secret Managerに登録済み |

---

## 予算アラート
- 請求先アカウント全体に対して¥10,000の予算アラート設定済み（50%・90%・100%）

---

## 追加作業ログ（2026-06-04）

### 完了
| タスク | 担当 | 内容 |
|---|---|---|
| 友人をIAMに招待 | 鉄田 | `ichisehiroshi@gmail.com` を **編集者(Editor)** で追加（コンソール） |
| CIデプロイ用SA作成 | 鉄田 | `publishr-ci-deployer@publishr-498123.iam.gserviceaccount.com`（runtime用 `publishr-runner` と分離）。付与ロール：Cloud Run 管理者／Cloud Build 編集者／サービス アカウント ユーザー／Artifact Registry 書き込み／ストレージ管理者 |
| SAキー発行・退避 | 鉄田 | JSONキー発行→**git管理外**へ退避：`C:\Users\ytets\.gcp-keys\publishr-ci-deployer.json`（リポにはコミットしない） |
| GitHubリポジトリ作成 | 友人 | `hiroshiichise/publishr`（**個人アカウント所有**）作成済・鉄田はCollaborator。**【2026-06-05完了】組織アカウント `cloud-dojo` 作成→`cloud-dojo/publishr` へ移管→鉄田にもオーナー権限付与済** |
| GitHub Secrets 登録 | 鉄田 | `GCP_PROJECT_ID` / `GCP_SA_KEY`(生JSON) / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` の4本を登録（※コラボレーター権限で登録可能だった） |

> ⚠️ **gcloud CLIは現状このPCで使用不可**：NortonのSSL/TLS検査（`Norton Web/Mail Shield Root`）がHTTPSをMITMし、gcloud同梱CAが弾く。検証オフは安全機構が不許可。上記はすべて**ブラウザのGCPコンソール＋ローカルPowerShell**で実施。詳細・回避策は `ERRORS.md` 参照。

### 残タスク
| タスク | 担当 | 状況 |
|---|---|---|
| ~~OAuth同意画面＋クライアント作成~~ | 鉄田 | ✅**完了（2026-06-04）**：Google Auth Platform設定（アプリ名`Publishr`・外部・**本番(未審査)**）／スコープ3つ（`drive.file`・`calendar.readonly`・`tasks.readonly`）／Webクライアント`Publishr Web`作成（リダイレクトURI=仮`http://localhost:8080/api/auth/google/callback`）／`GOOGLE_OAUTH_CLIENT_ID/SECRET`の2本をSecrets登録＝**Secrets計6本完了** |
| OAuth 残作業 | 鉄田/友人 | ①Drive/Calendar/Tasks **API有効化**（ランタイム前まで）②**本番リダイレクトURI**追記（バックエンドURL確定後）③**Testing/Production方針の握り**（G1-19・トークン7日失効回避） |
| Cloud BuildとGitHub連携 | 鉄田 | **【MTG 2026-06-05確定】方式A=GitHub App直結**。組織移管・鉄田オーナー権限は**✅2026-06-05完了**し所有者依存が解消されたため、**鉄田が GitHub App 直結で接続**（旧 Actions→`gcloud builds submit` の方式Bは不採用）。接続作業はW4 |
| ~~gcloud CLI × Norton の恒久解決~~ | 鉄田 | ✅**解決（2026-06-04）**：WSL2(Ubuntu/ARM64)導入＋gcloud導入で回避を実証（WSLはNortonのMITM対象外）。以後の開発はWSL側で。詳細→ERRORS.md |
| 「Cloud Build接続済みか」確認 | 鉄田 | 現状トリガー**未接続**を実機確認済（open-issues G1-18）。鉄田はオーナー権限取得済（2026-06-05）→方式Aで接続（W4） |

### GitHub関連の段取り（当初メモ／MTG 2026-06-05で更新）
1. ~~リポジトリ名：`publishr`、Visibility：Public で作成~~ → 作成済（現状は個人リポ。提出時にPublic化）
2. ~~鉄田のGitHubアカウントをCollaboratorに追加~~ → 完了
3. **【✅2026-06-05完了】組織アカウント `cloud-dojo` 作成→`cloud-dojo/publishr` へ移管→鉄田にオーナー権限付与済**
4. Cloud Build → トリガー → GitHubを接続（GCPプロジェクトID：`publishr-498123`）→ **方式A=GitHub App直結／鉄田が実施**（組織移管・鉄田オーナー権限完了で所有者依存が解消・W4）
5. `main`ブランチpushで自動ビルドのトリガー設定（W4）

---

## 参考URL

- GCPコンソール: https://console.cloud.google.com/home/dashboard?project=publishr-498123
- Firestore: https://console.cloud.google.com/firestore?project=publishr-498123
- Cloud Storage: https://console.cloud.google.com/storage?project=publishr-498123
- IAM: https://console.cloud.google.com/iam-admin/iam?project=publishr-498123
- Secret Manager: https://console.cloud.google.com/security/secret-manager?project=publishr-498123
- Langfuse: https://cloud.langfuse.com

---

## P1 実態確認（2026-06-06・[p1-gcp-setup-runbook.md](p1-gcp-setup-runbook.md) STEP A 実行結果）

> owner（ichisehiroshi@gmail.com）で WSL2 gcloud から確認（全体プラン `docs/planning/docs-replicated-bonbon.md` Phase 1）。**「無いものだけ作る」原則で実在を突き合わせた結果**。

### ✅ 実在を確認（既存・追加作成不要）
- プロジェクト `publishr-498123` ACTIVE・課金有効（`billingAccounts/01AEB4-E28B10-3EE3A0`）
- API 有効: aiplatform / run / cloudbuild / firestore / storage / pubsub / cloudscheduler / identitytoolkit / secretmanager / artifactregistry ＋ drive / calendar-json / tasks
- Firestore: `(default)` FIRESTORE_NATIVE `asia-northeast1`
- GCS: `gs://publishr-contents-498123`（ASIA-NORTHEAST1・publicAccessPrevention=enforced・UBLA=true）
- SA `publishr-runner`: aiplatform.user / run.invoker / **datastore.editor**（=docsの datastore.user を包含）/ storage.objectAdmin / secretmanager.secretAccessor
- SA `publishr-ci-deployer`: run.admin / cloudbuild.editor / iam.serviceAccountUser / artifactregistry.writer / storage.admin
- 他SA: firebase-adminsdk / firebase-app-hosting-compute / default compute（App Hosting 連携の痕跡）
- Secret Manager: `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`
- ADC quota project を `publishr-498123` に設定
- **Vertex Gemini 疎通スモーク成功**（gemini-2.5-flash・asia-northeast1・ADC・"疎通OK"）＝**P1のDoD達成**

### ⚠️ gap（要対応・主に owner/コンソール作業）
- **`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` が Secret Manager に無い**（Langfuse 3本のみ）。本ログ上部「Secrets計6本完了」と実態（3本）が齟齬。→ GitHub Secrets 側にあるなら住み分けを明記、backend が Secret Manager 参照なら OAuth クライアント値を登録。
- OAuth 同意画面（本番/3スコープ）・OAuth Web クライアントの実在＝**コンソール確認のみ**（CLI不可）。
- Firebase Authentication の Google プロバイダ有効化＝**コンソール確認**（identitytoolkit API は有効）。
- 予算アラート ¥10,000：CLI照会は quota project 制約（billingbudgets API 未有効）で未確認。**コンソール確認推奨**。

### 後回し（P1では作らない・P3〜P6）
- Cloud Run サービス / Cloud Run Job（曜日別×3）/ Cloud Scheduler / Pub/Sub `book-writing` / Artifact Registry リポジトリ / Firebase App Hosting backend / OAuth 本番リダイレクトURI 追記。
