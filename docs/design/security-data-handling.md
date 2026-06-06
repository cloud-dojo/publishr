# Publishr セキュリティ・データ取り扱い設計

> **目的**: Publishr が「何を」「どこに」保存し、「どの境界」で守り、「どのインシデント」を防ぐかを1枚で示す。Google Drive / Calendar / Tasks 連携、Firestore直アクセス、Cloud Run API、Vertex AI利用の公開前チェックリストを兼ねる。
> **関連正本**: API境界は [api-contract.md](api-contract.md)、Firestoreルールは [firestore-security-rules.md](firestore-security-rules.md)、GCP実態確認は [../infra/gcp-setup-log.md](../infra/gcp-setup-log.md)、未決/ゲートは [../planning/open-issues.md](../planning/open-issues.md)。
> **ステータス**: 2026-06-06時点の方針。現行コードはmock中心で、OAuth API・Firestore rules実ファイル・Cloud Run公開API認証は未実装。実装前に本書のゲートを満たす。

---

## 1. 基本方針

1. **ユーザーデータは本人単位で分離する**  
   Firestore上のユーザー資源は `uid` / `ownerUid` で所有者を判定し、本人以外に読ませない。

2. **秘密情報はFirestoreに置かない**  
   OAuth refresh token、OAuth client secret、Langfuse secret、サービスアカウントキーは Secret Manager / GitHub Secrets / ホスティング環境変数に置く。Firestoreには保存しない。

3. **Cloud Run APIはCORSではなく認証で守る**  
   `/healthz` 等の公開メタAPIを除き、Firebase IDトークンをサーバ側で検証する。リクエストbodyの `userId` は信用しない。

4. **Vertex AIは直接公開しない**  
   Vertex権限はCloud Run実行サービスアカウントに限定する。ユーザーからはFirebase認証済みAPIだけを経由させ、許可uid・レート制限・予約上限でコスト濫用を防ぐ。

5. **ログに秘密と生トークンを出さない**  
   access token、refresh token、認可コード、Authorizationヘッダ、サービスアカウントJSON、個人のDrive本文全文はログ/traceに出さない。

---

## 2. 保存対象と保存場所

| データ | 保存場所 | 書き込み主体 | 読み取り主体 | 主な防御 |
|---|---|---|---|---|
| Firebase AuthユーザーID | Firebase Auth / Firestore `users/{uid}` | Firebase / サーバ | 本人・サーバ | Firebase IDトークン検証、Firestore本人read |
| 初期プロフィール `initialProfile` | Firestore `users/{uid}.initialProfile` | フロント初回create | 本人・サーバ | Firestore rulesで本人のみ、初回/限定フィールドのみ |
| お気に入り著者 `favoriteAuthors` | Firestore `users/{uid}.favoriteAuthors[]` | フロント | 本人・サーバ | Firestore rulesで本人のみ、許可フィールド限定 |
| Google OAuth client ID | Secret Manager または環境変数 | owner/CI | Cloud Run | Secret Manager IAM、GitHub Secrets |
| Google OAuth client secret | Secret Manager | owner/CI | Cloud Run | Firestore保存禁止、ログ出力禁止、Secret Accessor最小化 |
| Google OAuth refresh token | Secret Manager（uid別secret名） | OAuth callback API | Cloud Run観測処理 | state検証、Secret Manager IAM、Firestore保存禁止 |
| Google OAuth access token | 原則永続保存しない（一時メモリ） | Cloud Run | Cloud Run | 短命、一時利用、ログ出力禁止 |
| OAuth `state` | 短命署名値（サーバ署名/短期保存） | OAuth start API | OAuth callback API | uid紐付き、期限付き、改ざん検知、再利用禁止 |
| Drive選択フォルダID | Firestore `users/{uid}.connectedSources.drive.folderIds[]` | サーバ | 本人・サーバ | サーバ書込、本人read、Drive Picker前提 |
| 連携状態 `connectedSources` | Firestore `users/{uid}.connectedSources` | サーバ | 本人・サーバ | クライアントwrite禁止、本人read |
| STEP0観測束 | Firestore `users/{uid}/observations/{YYYY-MM-DD}` | サーバ | 本人・サーバ | サーバ書込、本人read、クライアントwrite禁止 |
| Drive/Calendar/Tasksの生データ | MVPは観測束に必要範囲だけ保存 | サーバ | 本人・サーバ | 取得範囲最小化、±14日、Driveは選択対象のみ |
| plans | Firestore `plans/{planId}` | サーバ | 所有者 | `ownerUid` rules、クライアントwrite禁止 |
| booksメタ | Firestore `books/{bookId}` | サーバ | 所有者 | `ownerUid` rules、status/title/bodyUrl改ざん禁止 |
| feedback / 読書ログ | Firestore `books/{bookId}.feedback` | フロント | 所有者・サーバ | `feedback` フィールドだけ更新許可 |
| highlights | Firestore `books/{bookId}/highlights/{hid}` | フロント | 所有者・サーバ | 所有bookのみcreate/delete、update禁止 |
| personas | Firestore `personas/{personaId}` | サーバ | 認証済みユーザー | write禁止、公開範囲はMVP仕様に限定 |
| 本文Markdown/JSON | Cloud Storage `publishr-contents-498123` | WritingWorker | 所有者向けAPI/署名URL | publicAccessPrevention、UBLA、署名URL、推測困難パス |
| 表紙画像 | Cloud Storage | サーバ | アプリ表示 | public公開しない方針。必要なら署名URL/キャッシュ期限 |
| Langfuse trace | Langfuse Cloud | サーバ | 開発者 | token/本文全文を入れない、要約/score/URLのみ |
| Eval fixtures | repo `eval/` / `packages/shared-schema/fixtures/` | 開発者 | repo参加者 | デモ用・非秘密。実ユーザーsecret/tokenを混ぜない |
| GitHub Secrets | GitHub repository/org secrets | owner | GitHub Actions | 最小権限、環境保護、可能ならWIFへ移行 |
| サービスアカウントキー | 原則作らない。既存CI keyはGitHub Secrets | owner | CI | Workload Identity Federation推奨、ローテーション |

---

## 3. 保存しないもの

- OAuth refresh token / access token / AuthorizationヘッダをFirestore、Langfuse、通常ログ、フロントlocalStorageに保存しない。
- Google Drive全文を無制限に保存しない。MVPは選択フォルダ/ファイルと±14日の文脈に限定する。
- 本文100ページ相当の大きな生成物をADK session stateに溜めない。GCSを正本にし、stateには参照キー・要約だけ置く。
- サービスアカウントJSON、`.env`、秘密鍵、OAuth client secretをgit管理しない。
- `PUBLISHR_LLM=vertex` の実行結果に、ユーザー秘密やトークンをデバッグ出力しない。

---

## 4. アクセス境界

### 4-1. フロント

- Firebase AuthでGoogleログインする。
- Firestore直アクセスは、本人readと限定writeだけにする。
- Cloud Run API呼び出し時は `Authorization: Bearer <Firebase ID token>` を付ける。
- `NEXT_PUBLIC_*` には公開可能なFirebase設定値とAPI URLだけを置く。secretは置かない。

### 4-2. Cloud Run API

- `/healthz` 以外はFirebase Admin SDKでIDトークンを検証する。
- サーバ側の処理対象ユーザーは、bodyの `userId` ではなくトークン由来の `uid` で決める。
- 予約APIはFirestore transactionで所有者・状態・同時予約上限を確認する。
- 手動triggerはデモuid allowlistと連打防止を必須にする。
- OAuth callbackは `state` 検証に失敗したらトークン交換しない。

### 4-3. Firestore

- クライアントはFirestore Security Rulesに縛られる。
- サーバはAdmin SDKでrulesをバイパスするため、サーバ側にも所有者チェックを置く。
- `users/{uid}/observations/{date}` は本人read・サーバwrite専用にする。
- `books` / `plans` / `personas` の生成・状態遷移はサーバ専用にする。

### 4-4. Vertex AI / Imagen / GEAP

- GCP IAMでは `roles/aiplatform.user` をCloud Run実行SAに限定する。
- `allUsers` / `allAuthenticatedUsers` にVertex関連権限を付けない。
- API公開後も、未認証ユーザーがVertex実行パスに到達できないことをテストする。
- コスト上限は予約同時5冊、trigger allowlist、dev/prodフラグ、予算アラートで守る。

### 4-5. Cloud Storage

- `publicAccessPrevention=enforced` とUniform Bucket-Level Accessを維持する。
- 本文/表紙は原則非公開にし、必要な時だけ署名URLまたは所有者確認済みAPI経由で渡す。
- URLやパスだけで他人の本文を推測取得できない設計にする。

---

## 5. インシデント予防策

### 5-1. 誰でもAPIを叩ける事故

**起きること**: 未認証で予約・trigger・pipeline実行ができ、Vertexコストやデータ改ざんが発生する。

**予防**:
- FastAPI共通依存でFirebase IDトークンを検証する。
- `/healthz` 以外のAPIは認証なしなら `401`。
- 他ユーザー資源への操作は `403`。
- Cloud Run公開前に未認証/他人資源/許可uid外triggerのテストを通す。

### 5-2. Vertex AIの濫用

**起きること**: 公開API経由で誰でもGemini/Imagen/GEAPを起動し、課金が膨らむ。

**予防**:
- Vertex権限は `publishr-runner` など実行SAだけに付ける。
- triggerはデモuid allowlistに限定する。
- 予約同時上限5冊をFirestore transactionで守る。
- dev/prodフラグで本文ページ数・Imagen有効化・生成冊数を制限する。
- 予算アラートとログ監視で異常実行を検知する。

### 5-3. OAuth token漏えい

**起きること**: Google Drive/Calendar/Tasksへの長期アクセスが奪われる。

**予防**:
- refresh tokenはSecret Managerに保存し、Firestoreに置かない。
- access tokenは永続保存しない。
- `state` は短命・署名付き・uid紐付きにする。
- token/認可コード/AuthorizationヘッダをログやLangfuseに出さない。
- 漏えい時はGoogle OAuth client secretローテーション、対象refresh tokenの削除、Google側のアプリ連携解除を行う。

### 5-4. Firestore rules未適用

**起きること**: 本人以外が観測束・本・読書ログを読める/書ける。

**予防**:
- `firestore.rules` を実ファイル化し、本番接続前にデプロイする。
- emulator testで本人read、他人read拒否、禁止フィールドwrite拒否を確認する。
- `NEXT_PUBLIC_DATA_SOURCE=firestore` はrulesデプロイ後にだけ有効化する。

### 5-5. サービスアカウントキー漏えい

**起きること**: CI/CDやGCPリソースを第三者に操作される。

**予防**:
- 原則としてuser-managed keyを作らず、Workload Identity Federationを使う。
- 既存keyはGitHub Secretsにのみ置き、repoへ置かない。
- key利用権限をCIに必要なロールへ限定し、定期ローテーションする。
- 漏えい時は即時key無効化、GitHub Secrets差し替え、IAM Audit Log確認を行う。

### 5-6. ログ/traceからの情報漏えい

**起きること**: LangfuseやCloud Loggingに個人データ・token・本文全文が残る。

**予防**:
- ログはscore、round、decision、エラー種別、grounding URLなど最小情報にする。
- 個人文脈は必要なら要約・ハッシュ・件数にする。
- 例外ログでAuthorizationヘッダ、OAuth token、サービスアカウントJSONを出さない。

---

## 6. 公開前チェックリスト

Cloud Run公開、`DATA_SOURCE=firestore`、`PUBLISHR_LLM=vertex` のいずれかを有効化する前に確認する。

- [ ] `/healthz` 以外のAPIがFirebase IDトークン必須になっている。
- [ ] bodyの `userId` を信用せず、トークン由来の `uid` を使っている。
- [ ] 未認証API呼び出しが `401` になる。
- [ ] 他ユーザー資源への操作が `403` になる。
- [ ] `POST /api/trigger/planning` がデモuid allowlistで制限されている。
- [ ] trigger / reserve / LLM実行に連打防止または上限がある。
- [ ] OAuth `state` が短命・署名付き・uid紐付きで検証される。
- [ ] refresh tokenがSecret Managerに保存され、Firestoreやログに出ない。
- [ ] `firestore.rules` が実ファイル化・デプロイ済み。
- [ ] Firestore emulator testで本人/他人/禁止writeを検証済み。
- [ ] Vertex権限がCloud Run実行SAに限定され、`allUsers` / `allAuthenticatedUsers` に付与されていない。
- [ ] GCSバケットのpublicAccessPreventionとUBLAが有効。
- [ ] `.env`、サービスアカウントJSON、OAuth secretがgit管理されていない。
- [ ] GitHub Secrets / Secret Managerの必要secret名と参照先が一致している。
- [ ] 予算アラートと最低限のCloud Logging確認手順がある。

---

## 7. インシデント時の初動

| インシデント | まず止めるもの | 初動 |
|---|---|---|
| API濫用/Vertexコスト増 | Cloud Run serviceの公開経路、trigger | Cloud Runを非公開または一時停止、allowlist縮小、Audit Log確認 |
| OAuth token漏えい | 対象refresh token / OAuth client secret | Secret削除、client secretローテーション、Googleアカウント側の連携解除 |
| Firestore誤公開 | Firestore rules / App Hosting本接続 | deny-allルールへ一時切替、`NEXT_PUBLIC_DATA_SOURCE=mock` へ戻す |
| SA key漏えい | 該当key | key無効化、GitHub Secrets差し替え、IAM権限棚卸し |
| GCS本文漏えい | 署名URL / bucket IAM | 署名URL失効待ち、公開権限撤去、対象object移動/再発行 |
| Langfuse/ログ漏えい | trace送信 / ログ出力 | trace無効化、該当trace削除、redaction追加 |

---

## 8. 実装時のDoD

- API実装者は、認証なし/他人資源/許可uid外のテストを追加する。
- Firestore実装者は、rules本文だけでなくemulator testを追加する。
- OAuth実装者は、`state` 検証失敗時にトークン交換しないテストを追加する。
- Vertex接続実装者は、Cloud Run公開URLから未認証で実行できないことを確認する。
- CI/CD実装者は、user-managed keyの代替としてWorkload Identity Federationを検討し、難しい場合はローテーション手順を残す。
