# 本番ライブ化（C3.3 / C4.1 / C1.1 実観測）— 問題点と残タスク

最終更新: 2026-06-15（一瀬）

mock 既定だった本番を「実 GCS 本文退避（C3.3）・実 OAuth/Drive Picker（C4.1）・**手動トリガーの実 Google 観測（C1.1）**」へ切り替えた作業で判明した問題点・暫定対応・残タスクの一覧。

正本の状況サマリは `docs/planning/wbs.md`。本書は本番ライブ化の運用ハマりどころに特化する。

---

## いま動いていること（検証済み）

- **C3.3 live**: published 本文を非公開バケット `publishr-contents-498123` へ退避（`PUBLISHR_BODY_STORE=gcs`）。`GcsBodyStore.put→get` を実バケットで検証。runner SA は `roles/storage.objectAdmin` 保有。
- **C4.1 live**: OAuth サーバ流が本番で完走（同意 → callback → token 交換 → Secret Manager 保存 → connectedSources 更新）。Drive Picker（GIS）でフォルダ選択 → `folderIds` を Firestore 保存。
- **C1.1 実観測 live**: `POST /api/trigger/planning` が接続済みユーザーの**実 Drive(選択フォルダ)/Calendar/Tasks** を読み、実データから企画 → 入荷。2026-06-15 に佐倉(publishr.hackathon)の実 Drive を読んで **5冊生成**（`booksAdded:5`・515秒）を確認。未接続/トークン無し/失敗時は fixture へ自動フォールバック。

### 現在の本番 BFF env（`publishr-api` / Cloud Run / asia-northeast1）
`DATA_SOURCE=firestore`・`PUBLISHR_LLM=vertex`・`GOOGLE_CLOUD_LOCATION=us-central1`・`PUBLISHR_OBSERVE=google`・`PUBLISHR_OAUTH_TOKEN_STORE=secret_manager`・`PUBLISHR_SECRET_MANAGER_PROJECT=publishr-498123`・`PUBLISHR_BODY_STORE=gcs`・`PUBLISHR_REQUIRE_RESERVE_AUTH=1`・`DEMO_UID=5JLLGOc3rpXiGN9KXmsISBNAKty2`。

---

## 問題点・残タスク

| # | 重大度 | 領域 | 問題 | 対応 | 状態 |
|---|---|---|---|---|---|
| 1 | 高 | 速度/可用性 | 実Vertex で5冊同期生成＝**515秒**。Cloud Run HTTP 上限 **600秒**に近く、Drive増・遅延で **504** 落ちのリスク | **企画を Pub/Sub 非同期化**（`/api/worker/plan`）＋ack_deadline 600s | ✅実装（2026-06-15・`feat/c2-planning-async`）／infra設定で有効化 |
| 2 | 高 | 正当性/安全 | `/trigger/planning` の `user_id` 既定が **`u_sakura`**（fixture）→ 実フォルダでなく **`fld_work` を Drive 照会 → 404**。UI は正しい uid を送るのでデモは可だが脆い | body を信用せず**検証済み uid** を使う（C4.9） | 未 |
| 3 | 中 | クォータ | Vertex **429 RESOURCE_EXHAUSTED**（`asia-northeast1` の Pro クォータ枯渇）で企画が落ちていた | `GOOGLE_CLOUD_LOCATION=us-central1` に切替 | ✅暫定対応済 |
| 4 | 中 | セキュリティ | `GOOGLE_OAUTH_CLIENT_SECRET`・`PUBLISHR_OAUTH_STATE_SECRET` が**平文 env**（コンソール権限者は閲覧可・作業中に露出） | Secret Manager 移行＋**ローテーション** | 未 |
| 5 | 中 | セキュリティ | per-uid トークン保存のため runner SA に **`roles/secretmanager.admin`**（広い＝全 secret 読み書き可） | カスタムロール（`secrets.create`＋`versions.add/access` のみ）へ scope-down | 未 |
| 6 | 中 | 運用/可観測性 | 本番で **INFO ログが出ない**（`main.py` に logging 構成無し＝root 既定 WARNING）。`observe:`/`trigger ok` が見えず切り分けに難。WARNING/ERROR は出る | `logging.basicConfig(level=INFO)` 等を追加 | 未 |
| 7 | 中 | UX | UI から**企画を再実行できない**（`runPipeline` は first-run 状態でのみ発火＝localStorage gated）。既存ユーザー（佐倉=ready）は再生成不可・手動「今すぐ企画」ボタン無し | 再生成アクション追加 or first-run リセット導線 | 未 |
| 8 | 中 | ビルド | `gcloud run deploy --source .` は**ルート `Dockerfile`** を使うが `apps/api/Dockerfile` の同名コピーが存在。誤って後者を編集すると**本番に反映されない**（実際に extra 同梱が空振りし `google-auth-oauthlib` 欠落 → token 交換 ModuleNotFoundError が発生） | ルートを正本化（コメント済）／将来は1本化 | ✅原因対応済（重複は残） |
| 9 | 低 | デモ品質 | 実観測は**佐倉の実 Google の中身**を「今」基準±14日で読む。アカウントが空だと本が薄くなる | publishr.hackathon の Drive(選択フォルダ)/Calendar/Tasks にデモ用コンテンツを直近日付で投入 | 運用 |
| 10 | 低 | デモ運用 | web を firestore 全面切替したため**匿名訪問者はログイン要求/空棚**（mock時は公開閲覧できた） | デモは佐倉でログインして提示 | 運用 |
| 11 | 低 | C3.3 | 署名URL直リンクは runner SA の **SignBlob 権限**が要る（現状未付与）。reader は server-side read のため通常は不要 | 直リンクが要るときのみ `roles/iam.serviceAccountTokenCreator` 付与 | 任意 |

---

## 詳細

### #1 同期企画が重い（515s / 上限600s）
`mode_a_service.run` が `run_mode_a_pipeline` を**同期**で回し、`PUBLISHR_MAX_BOOKS_PER_RUN=5` × 実 Vertex（reader/subs+grounding/owner/leader/persona/author/editor/cover）で 515 秒。Cloud Run のリクエスト上限 600 秒に近い。
- **即効**: `PUBLISHR_MAX_BOOKS_PER_RUN=1〜3`（1冊 ≈ 数分・3冊 ≈ 300s 目安）。
- **本筋**: 予約(モードB)と同様 **Pub/Sub 非同期化** → トリガーは即 200 を返し、本は Firestore 購読で順次流入。`persist_arrivals` を逐次化すると体感も改善。

### #2 トリガーの user_id 既定が u_sakura
`apps/api/publishr_api/schemas.py` の `TriggerPlanningInput.user_id = "u_sakura"`。body 省略/既定だと fixture ユーザーを観測対象にし、その `connectedSources.drive.folderIds = ['fld_work']`（fixtureのダミー）を実 Drive へ照会して 404。
- 本番は `api_trigger_planning` で**検証済み `uid` を user_id にも採用**（body の user_id を信用しない／少なくとも uid と一致を要求）。`observe_uid` は既に検証済み uid を使用済み。

### #3 Vertex 429（リージョン）
`asia-northeast1` の Gemini Pro クォータが枯渇し企画が 429。`GOOGLE_CLOUD_LOCATION=us-central1` で解消（mode_b/eval も us-central1 で実績あり）。
- 留意: 観測データ（佐倉の Drive 本文）が us-central1 で処理される（データ所在）。本番要件次第で要再検討。Imagen は `PUBLISHR_IMAGEN_LOCATION`（既定 us-central1）で別管理。

### #4/#5 シークレットと IAM
- OAuth の client secret / state secret を Secret Manager 参照（`--update-secrets`）に移し、平文 env を削除＋**ローテーション**（client secret はコンソールでリセット）。Langfuse 3鍵と同じ方式。
- runner SA の `secretmanager.admin` は広い。per-uid トークン用に `secretmanager.secrets.create`＋`versions.add`＋`versions.access` のみのカスタムロールへ。

### #6 本番 INFO ログ
`mode_a_service._observation_source` は実Google/fixture の別を `logger.info("observe: …")` で出すが、本番では root logger 既定（WARNING）で抑止され不可視。`main.py` で INFO を有効化すると、実観測が走ったか即確認できる。

### #7 企画の再実行導線
`apps/web/src/app/(shell)/page.tsx` の `runFirstRun → runPipeline` は `firstRunStatus==="generating"`（localStorage・per uid）のときだけ発火。既存ユーザーは UI から再企画できない。デモ/検証用に「今すぐ企画」ボタンか first-run リセットが要る。暫定は API 直叩き（`POST /api/trigger/planning` ＋ `userId=<uid>`）。

### #8 Dockerfile 重複
ルート `Dockerfile` が本番ビルドの正本（`--source .`）。`apps/api/Dockerfile` は同内容コピー。今回 `apps/api/Dockerfile` だけに extra を足してしまい本番イメージに `agents[google]`/`apps/api[gcs,secret-manager]` が入らず、OAuth token 交換が `ModuleNotFoundError(google_auth_oauthlib)` で失敗。ルートに反映して解消。将来は symlink か単一ファイル化で二重管理をやめる。

---

## 推奨着手順（デモ信頼性優先）
1. **#1 冊数を絞る**（`PUBLISHR_MAX_BOOKS_PER_RUN=3`）＝即効・低リスク。
2. **#2 user_id を検証済み uid に**＝誤観測/404 の除去。
3. **#6 INFO ログ**＝以後の切り分けが速くなる。
4. **#4/#5 シークレット/IAM ハードニング**＝提出前のセキュリティ。
5. **#7 再実行導線** / **#1 非同期化**＝デモ体験の作り込み。
