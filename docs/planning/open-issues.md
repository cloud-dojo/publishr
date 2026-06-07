# Publishr 未決論点台帳

> **役割**: 各設計ドキュメントに散在していた「未確定／未決／友人MTGで詰める」論点を1枚に集約した台帳。各docの未確定セクションはここを参照する。
> **凡例**: 🔴未決 ／ 🟡方針あり・要確認 ／ ✅決着（下部のログ参照）。各論点に【出典】を付す。
> **前提**: PatentSentinel（代替案）は不採用。**撤退はしない＝Publishrをやりきる**前提のため、撤退基準・採用GO判断の論点は持たない。
> **全体の目次は [正本マップ](../README.md)。**
> **🧭 現在地（2026-06-05）**: 環境系の論点（OAuth保存先G1-5・GCP構築・Secrets）は決着。**鉄田単独の先行タスクも完了**＝G1-9(initialProfile)✅・G1-20(gcloud×Norton)✅・G1-10(Eval Set 8件)✅。デモはカット割り廃止→動画台本2本立てへ置換✅。**友人MTG（2026-06-05）完了＝着手前の決定ゲートを全件クローズ**＝G1-1(ADK・一旦これでいくで合意)✅／G1-2(役割・基本合意)✅／**G1-13(Drive Picker＝フォルダ単位・Picker前提で確定)**✅／G1-15(通知FCM不要)✅／G1-18(Cloud Build＝方式A・組織化で確定)✅／G1-19(OAuth Production維持)✅／G1-3/5/6/7(連携・確定)✅／I-19/I-9/I-20(データ詳細・確定)✅。**残＝G1-17(Langfuse実装方式)は先送り（今後検証）**。これでW1着手可。

---

## 着手前に「決める」論点（✅ 友人MTG 2026-06-05で全件決着）

| # | 論点 | 状態 | 決め方／出典 |
|---|---|---|---|
| G1-1 | ADK実現可能性の握り（W1 Hello Worldの範囲） | ✅方針合意（MTG 2026-06-05） | **論点は残るが「一旦これでいく」で合意**＝W1 Hello Worldで実証しながら進める（escalate/max_iterations・構造化出力等）。W1末(6/14)までに動かなければSTEP2のみLangGraphへ逃げるNGラインも合意【ARCH §12・ADK §9】 |
| G1-2 | 役割分担（友人＝エージェント／鉄田＝フロント） | ✅基本合意（MTG 2026-06-05） | 役割分担を基本合意。Eval責務境界（設計=鉄田／ハーネスv2実装=一瀬・I-21）も確定。**ただし基盤Firebase部分（Firestore/GCS）の担当は未定＝鉄田が一瀬を補助する可能性あり・後決め**【ARCH §5・roles-and-ops.md】 |
| G1-3 | フロント⇔バック連携方式（Firestore直書き＋最小API3本） | ✅確定（MTG 2026-06-05） | デフォルト案（Firestore直書き＋最小API3本・予約はPOST /reserve の明示API）で異論なく確定【AGENT §10-5/§11・API §6-2】 |
| G1-4 | `ownerUid` フィールド方式 vs サブコレクションネスト | 🟡ownerUid方式で原典反映済 | ネストに覆す場合は要再変更【FIRESTORE §2/§5-1・API §6-5】 |
| G1-5 | OAuthトークンの保存先（Secret Manager か Firestore暗号化） | ✅決着 | **Secret Manager で確定**（infra/GCP環境構築ログ.md・Langfuseキー登録済み・2026-06-03）【API §6-1】 |
| G1-6 | 手動トリガーの認可範囲（デモ垢限定か全ユーザー可か） | ✅確定（MTG 2026-06-05） | **`POST /api/trigger/planning` を許可uidリスト（デモ垢のみ）に制限＝コスト暴走防止**（将来レート制限）で確定。MTGアジェンダ §3-4【API §6-3】 |
| G1-7 | フロント本番ホスティング／APIベースパス／CORS | ✅確定（MTG 2026-06-05）／✅**App Hosting 2026-06-06 live** | **ホスティング＝Firebase App Hosting で確定（フロント＝`apps/web`/Next.js＝G1-11も解消・2026-06-04）**。**✅2026-06-06 App Hosting backend 作成＋GitHub App 連携完了→mock公開中**（`publishr--publishr-498123.asia-east1.hosted.app`）。Turbopack×npm workspaces 問題を解消（root `workspaces`削除・shared-schemaベンダーコピー）しbuild-010で成功。リージョン=`asia-east1`。**CORS/ベースパス確定＝API は単一Cloud Runに `/api/*` 集約・フロントは `NEXT_PUBLIC_API_BASE_URL` 注入／CORS許可＝App Hosting本番ドメイン＋`localhost:3000`・GET/POST・Authorization+Content-Type・cookie不使用**（MTGアジェンダ §3-4）【API §6-4・CICD §3】 |
| G1-8 | 企画リーダーのスコア閾値・満点定義 | 🟡仮置き70/100 | MVPは4観点×各25点・閾値70。運用調整【AGENT §10-7・ADK §9-10・MVP §8】 |
| G1-9 | initialProfile 選択肢リスト（業界/職種/役職/関心/読書傾向） | ✅決着 | **2026-06-04確定**＝5ステップ（業界13/職種11/役職7/関心19/読み口7）を `apps/web/src/data/profileOptions.ts`（正本）に実装（`apps/mockup/...` は同内容の参照コピー）。叩き台 `../design/api-contract.md` §2-a 準拠【MVP §8】 |
| G1-10 | Eval Set 8件の実データ作成 | ✅決着 | **2026-06-04確定**＝`eval/eval_set.yaml` に8件（eval_01–08・4観点0-100/expectedBand）＋境界2件（eval_b1/b2）を full data で実装済。WBS A4.1=✅・TOP5クローズと整合（残＝judgeハーネス実装は別論点 I-21）【MVP §8】 |
| G1-11 | フロントUIテンプレ／ライブラリ選定 | ✅確定（MTG 2026-06-05） | **フロント＝Next.js（`apps/web`）で確定（2026-06-04）**。モックアップ（`apps/mockup`/Vite）はデザイン参照専用に降格。**front/back 共有スキーマの正本＝`packages/shared-schema`（`@publishr/shared-schema`）に置く方針・改善方針も確定。スキーマ内容の更新は鉄田が引き継ぎ実施**（型ドリフト防止）【ARCH §12・本台帳B7由来】 |
| G1-12 | サンプルDrive準備 | ✅完了 | 佐倉美咲ペルソナで Drive10/Calendar28/Tasks15 整備済（2026-06-02）。デモ再現性の要【ARCH §12】 |
| G1-13 | **drive.file のファイル選択方式（Google Picker 連携）** | ✅確定（MTG 2026-06-05） | `drive.file` はアプリがDrive内を走査・一覧**できない**（ユーザーが選んだものだけ）ため、**Google Picker前提で確定／選択粒度＝フォルダ単位でユーザーが指定**。`connectedSources.drive.folderIds[]` でサーバ保持。フロント＝Picker UI(鉄田)／バック＝ID保存・読取(一瀬)【ARCH §3/§6-5・API §2-a/§4】 |
| G1-14 | STEP0でCalendar/Tasksを消費する仕様 | ✅確定（取得範囲）／🟡grounding課金残 | **取得範囲＝±14日（過去2週＋先2週）・生データのみ（要約しない）で確定（2026-06-03）**。Calendar/Tasksは確定インプットへ格上げ済（AGENT §2／ARCH §1・§3整合済）。STEP1 currentWork（局面・課題・upcomingKeyEvents）へ反映。**3ソース疎通はW1で確認の段取りで合意（MTG 2026-06-05）**。残＝調査サブB/CのGoogle検索grounding課金影響はW1疎通で確認【AGENT §2・MVP §3 #1】 |
| G1-15 | **入荷/執筆完了の通知方式** | ✅確定（MTG 2026-06-05） | デモ カット3「入荷通知」・カット5「予告通知」が依存。**MVP=アプリ内 Firestore購読＋トースト/バナーで確定（FCMプッシュ不要）**。FCM工数化はしない【デモシナリオ カット3/5・UI 3-8】 |
| G1-16 | **LLMコスト概算と上限ガード方針** | 🟡ドラフト済 | `../design/cost-estimate.md` 作成済（ハイブリッド＋予約上限5冊＋編集ループ）。dev/prodガードは `.env.example` に追加済（BODY_PAGE_COUNT/ENABLE_IMAGEN/BATCH_BOOKS_OVERRIDE）。残＝W1実測で実値上書き |
| G1-17 | **Langfuseトレース仕様（必然性の証跡）** | 🟡先送り（MTG 2026-06-05） | `../design/langfuse-tracing.md` 作成済（企画スコアループ・編集ループ2系統・調査groundingの取得URLをspan属性で残す）。**実装方式（OTel経由 or Langfuse SDK直）・grounding取得元フィールドは現時点で判断不可＝先送り。今後W1疎通以降に検証しながら確定**。3シグナル設計自体は維持。実装は一瀬・W4以降【CICD §5】 |
| G1-18 | **Cloud Build↔GitHub接続方式** | ✅確定（MTG 2026-06-05）＝方式A | **GitHub組織アカウント `cloud-dojo` への移管・鉄田オーナー権限付与は✅2026-06-05完了→所有者依存が解消されたため、鉄田が GitHub App 直結（方式A）で Cloud Build↔GitHub を接続**で確定（旧推奨B＝Actions主導は不採用）。鉄田のGitHub Secrets登録はコラボレーター権限で可能と実機確認済（2026-06-04・4本登録済）。Cloud Buildトリガーは現状**未接続**。実装はW4【CICD §3・GCP環境構築ログ.md 2026-06-04】 |
| G1-19 | **OAuth同意画面の公開ステータス（Testing vs Production未審査）** | ✅確定（MTG 2026-06-05）＝Production維持 | **Testingモードはリフレッシュトークンが7日で失効**→週次自律バッチ（Cloud Scheduler×Secret Manager保存トークン）が1週間後に停止しPublishrの自律性が壊れる。**Production(未審査)ならトークン長期有効**（未審査警告はバイパス可・100ユーザー上限）。現状Production設定済（2026-06-04）。**Production維持で確定**（OAuth実装担当=一瀬へ認識共有済）【G1-5・API §6-1・GCP環境構築ログ.md 2026-06-04】 |
| G1-20 | **gcloud CLI×Norton のHTTPS検査でCLIが通らない** | ✅決着 | **2026-06-04 恒久対処完了**（W1のADK/デプロイでgcloud CLIが利用可能に）。※対処方式の詳細は `GCP環境構築ログ.md` に追記のこと【GCP環境構築ログ.md 2026-06-04】 |
| G1-21 | **Cloud Run公開前のセキュリティゲート（API認証・Vertex濫用防止）** | 🟡方針確定・実装前 | **2026-06-06再確認**: GCP IAM上は `roles/aiplatform.user` が `publishr-runner` のみで、`allUsers`/`allAuthenticatedUsers` へのVertex権限は見えない。Cloud Run service/jobも未作成。ただし現行 `apps/api` はFirebase IDトークン検証が未実装のため、公開すると誰でもBFF操作・将来のVertex実行を間接起動できる。C4.9前ゲートとして ①FastAPI共通依存でFirebase IDトークン検証 ②body `userId` を信用せずトークンuidを使用 ③triggerはデモuid allowlist+連打防止 ④OAuth `state` は短命・署名付き・uid紐付き ⑤`firestore.rules` 実ファイル化/デプロイ/emulator test ⑥Cloud Run公開後も未認証=401/他人資源=403を確認、を必須化【API §2/§4・FIRESTORE §0・infra/gcp-setup-log.md セキュリティ再確認】 |

---

> ⚠️ E2E縦通し・ADK学習・工数食い合い等の技術リスクは `技術アーキテクチャ.md` §11 のリスク表で管理（撤退判定ではなく、対策で乗り切る）。

## W1 Hello Worldで実証するADK技術論点

> 記憶での断定をせず、W1で公式ドキュメント/SDKに対して実証する（スキル `google-agents-cli-adk-code` 参照）。【出典：ADK §9】

1. ワークフローエージェントのクラス名・入れ子可否（Sequential/Parallel/Loop、Loop内にParallel＋LlmAgent）
2. ループ脱出の正式手段（`escalate`・`max_iterations` の挙動）。**v2で LoopAgent は2系統**＝STEP2企画壁打ち（最高3R）と編集ループ（STEP4プレビュー1R／モードB本文 最高3R）。同一機構の使い回しで実証する
3. session state の読み書きAPI（output_key／state注入）
4. 構造化出力の強制（Pydantic・PersonaGenerator員数5人厳守・LeaderVerdictスコア型）
5. モデル指定の粒度（エージェント単位でFlash/Pro切替）
6. Cloud Run JobでのADK Runner起動（認証・Vertex権限・曜日別ジョブの起動パラメータ themeKind/STEP0-1フラグ）
7. Google検索 grounding の有効化（調査サブB市場・Cテーマ知見・取得URL出力）

---

## 実装中に詰める（作りながら）

| # | 論点 | 状態 | メモ／出典 |
|---|---|---|---|
| I-1 | スコア閾値の最終値の運用調整 | 🟡仮置き70 | 実データで調整【ADK §9-10・AGENT §10-7】 |
| I-2 | ephemeralペルソナの削除ポリシー | 🟡方針あり | お気に入り登録時に永続化／未選択draftクリア時に削除。MVPは削除不要【ADK §9-9】 |
| I-3 | 生成ペルソナの保存タイミング（STEP3a→3b前に保存完了） | 🟡方針あり | 並列実行時の競合回避【ADK §9-8】 |
| I-4 | 差し戻し時にサブを再実行するか | 🟡既定しない | 担当者が既存サブ成果で練り直す。コスト次第で再実行余地【AGENT §10-10】 |
| I-5 | initialProfile の変更可否 | 🟡MVPは変更不可→**実質本人編集可へ前進（2026-06-07）** | 次サイクルのDrive観測で profile 自然更新。将来は設定画面。**2026-06-07：アカウントのプロフィール編集が機能（業界/職種/役職/関心/読み口/出会いの幅をいつでも更新可）＝I-6のルール緩和で本人再書込を許可**【API §6-6】 |
| I-6 | initialProfile 書込制限の実装（初回のみcreate） | 🟡方針あり→**2026-06-07：初回限定を撤廃** | 旧：ルールの affectedKeys で「initialProfileは初回のみ」を表現。**ただし seed の `initialProfile:null` が存在すると onboarding 書込が permission denied で黙って失敗→登録ボタン固まりの原因に**。**2026-06-07：`users/{uid}` update を `onlyChanged(['initialProfile','favoriteAuthors'])` のみ（本人なら何度でも書込可）に緩和・再デプロイ**。`profile`/`connectedSources` 等のサーバ専用フィールドは引き続き保護【FIRESTORE §5-5・WBS C3.1】 |
| I-7 | favoriteAuthors の上限件数 | 🟡MVP10件上限 | 超過は古いものから削除 or UI制限【API §6-7】 |
| I-8 | favoriteAuthors の参照方式 | 🟡コピー保持推奨 | name/style をコピーしorphan防止【FIRESTORE §5-6】 |
| I-9 | 読書ログの置き場所（feedback集約 か logs/サブコレクション） | ✅確定（MTG 2026-06-05） | **`books/{bookId}.feedback` に集約（`{rating,wantsSequel,readPercent,dropped}`）／ハイライトのみサブコレクション** で確定→ ルールが `onlyChanged(['feedback'])` 1行で済む。滞在ログ(dwellSec)はMVP対象外【FIRESTORE §5-2】 |
| I-10 | 本文(GCS)の保護（署名付きURL/IAM） | 🟡優先度中 | Firestoreルール範囲外。提出リポジトリに残すなら明記【FIRESTORE §5-3】 |
| I-11 | personas 読み取りを全認証ユーザーに開放してよいか | 🟡MVPは可 | 商用化時に再検討【FIRESTORE §5-4】 |
| I-12 | 編集長の本文ルーブリック（執筆品質の採点観点） | ✅確定 | **5観点で確定（2026-06-03）**：①構成の一貫性 ②各章の掴み（引き込み） ③読者状況への的中 ④著者ペルソナの一貫性 ⑤実践性・具体性（行動に落ちる・水増し検出）【AGENT §7】 |
| I-13 | 実在著者モデル参照の知財リスク | 🟡架空化方針 | 実在著者は作風参考に留め、名前・経歴は架空。規約の知財条項も要確認【構想 §10-11・ARCH §12】 |
| I-14 | デモのデータ戦略（ライブ生成 vs seed再生） | 🔴未→🟡足場前進（2026-06-07） | LLM出力は非決定的。録画再現性のため「seed投入＋必要箇所だけライブ」を想定。fixtures→Firestore/GCS のseed投入機構を作るか判断。W5録画直前の事故回避。**2026-06-07：Firestore運用スクリプト整備**＝`scripts/seed_firestore_rest.py`（投入）／`inspect_firestore.py`（棚卸し）／`cleanup_firestore.py`（限定削除・ドライラン既定）／`fix_user_name.py`（name修正）／`patch_book_bodies.py`（本文投入・存在チェックで孤児doc生成防止）。本番Firestoreのテストデータ整理（孤児book/レガシーuser削除・鉄田佐倉name修正）を実施済【MVP §5-1・デモシナリオ】 |
| I-15 | Firestore複合インデックス／クエリ形状の早期確定 | 🔴未 | 棚・書庫クエリ（ownerUid×status×themeKind×createdAt降順・favorite等）は複合インデックス必須。クエリ形状を早めに列挙し `firestore.indexes.json` を用意（Terraformにも乗せる）。後出しは実行時エラーで露見【API §1・ARCH §3】 |
| I-16 | 予約上限の単位と執筆スロットル | ✅確定（単位）／🟡スロットル残 | **同時最大5冊で確定（2026-06-03）**＝reserved+writing の合計が5冊以上で予約拒否（API §3）。執筆並列度（1日1冊等の処理スロットル）は実装時に調整【MVP §5-2・API §3】 |
| I-17 | セレンディピティの冊数（5冊 or 3冊） | 🟡暫定5冊維持 | 暫定は本命5＋セレンディピティ5＝週15冊。3冊に絞ると週13冊。デモ・コスト・物語のバランスで判断【MVP §5-2】 |
| I-18 | STEP4プレビュー編集ループの合格閾値 | 🟡仮置き | **プレビュー＝総合50/75＋足切り10（仮置き）／本文＝総合70/100（仮置き）**。企画リーダー（70/100）より緩め。明らかな不足のみ1Rで弾く水準を実データで運用調整（C5.5）【AGENT §5-2b・§7・prompts step4_editor_preview/modeB_editor_body】 |
| I-19 | **ObservationBundle（観測ログ）の保存先コレクション** | ✅確定（MTG 2026-06-05）→クローズ | 推奨パッケージのまま異論なく確定＝**`users/{uid}/observations/{YYYY-MM-DD}` サブコレクション（日付docID＝冪等）に フル束をインライン保存・サーバ書込/本人read。生テキストのGCS分離・retention/TTLは将来F項目**。tech-arch §3／AGENT §2・付録／FIRESTORE §1・本文に match 追加／WBS C3.4 に反映【AGENT §2・FIRESTORE §1・ARCH §3】 |
| I-20 | **エラー/リトライ/冪等/タイムアウト方針** | ✅確定（MTG 2026-06-05）→クローズ | MVP最小方針のまま異論なく確定＝**①reserveは Firestore transaction で count確認→条件付き`draft→reserved` ②Pub/Sub冪等＝status が writing/published ならスキップ（bookId基準・messageId不要） ③モードA Job失敗＝ログ＋手動再実行（自動リトライなし） ④本文100pは章ごと分割保存で途中再開可＝Cloud Runタイムアウト上限内**。W1で dev最小構成の実行時間を実測【ADK §6・API §3】 |
| I-21 | **v2 Evalハーネスの再構築（LLM-judge化）** | 🔴未（一瀬・GEAP判定本体） | **【2026-06-06 裏取り更新】** `scripts/eval_harness.py`＋`apps/api/tests/test_eval_harness.py` は **v2整合済み・テスト緑**（commit `c06b143`「P0a mock回帰復旧 — eval_harness を v2 eval_set.yaml と整合」／`pytest tests/test_eval_harness.py`=2 passed）。現harnessは①**mock決定的回帰の床(H0a)**（`run_pipeline`＋`plan_relevance` 等は旧構想の残骸ではなく意図的に残す決定的チェック）＋②**v2 `eval/eval_set.yaml` の構造検証**（`load_eval_cases`/`validate_eval_set`・`cases` 8件=eval_01–08・`expectedBand`・`borderlineCases` 2件）を実装。**残＝Vertex Gen AI Eval Service（GEAP）による実 LLM-judge 採点ゲートの実装**（自作judgeでなくVertex接続＝一瀬）。**v2ハーネス（LLM-judge本体）＝`eval_set.yaml` を Gemini judge（`packages/prompts/eval_judge.md` と同一ルーブリック）で採点し、`cases`(8件・7/8でゲート)と `borderlineCases`(診断・C5.4/5.5)を読む** へ再構築。**Eval設計＝鉄田✅／ハーネス実装＝一瀬**。C5.1プロンプト実テスト・C5.3 CIゲート・C5.4再現性の前提。MTGアジェンダ §2。**【2026-06-05 実装ルート】v2ハーネスは Vertex AI Gen AI Evaluation Service（GEAP＝旧Vertex AI）で実装が有力**＝自作judgeより軽く、基準5の"純正運用"訴求に直結。動くコード＋設計＝対外資料 `publishr_other/GEAP②_EvalService具体化.md`（`from vertexai.evaluation import EvalTask, PointwiseMetric`／`metric_prompt_template`へ`eval_judge.md`移植／`CustomMetric`で構造化確実版／kind別ゲート 本命≥70+足切り/ずれ≤40/セレンディピティ30-60・8件中7/`borderlineCases`診断除外／CI差し替え・judge=Vertex Gemini Pro）【AGENT §8・eval_set.yaml 冒頭注記・WBS C5.3/C5.4・publishr_other/GEAP②】 |
| I-22 | **初回体験（first-run）の実15冊生成パイプライン未実装** | 🔴未（firestoreは空振り・C1依存） | 登録直後の「空→生成中→15冊」初回体験は**mockでは決定的15冊（本命10＋セレンディピティ5・`apps/web/src/data/firstRunCatalog.ts`）の時間差入荷で動作**（`runFirstRun`・生成中UI・2026-06-07）。**firestoreモードは`runFirstRun`→`/api/trigger/planning`を叩くだけで実15冊をFirestoreに書く処理が無い**ため生成中UIが空振り→45秒安全タイムアウト/手動「書店を見る」で空書店へ抜ける（詰まりはしない）。実生成は**C1.1–C1.6（モードA全STEP）＋初回まとめ生成のAPI/Job**に依存。デモはmockサンドボックスで見せる前提【WBS C4.2/C1・2026-06-07】 |
| I-23 | **lint（make verify の lint-web）** | ✅緑（誤認訂正・2026-06-07） | 当初「赤」と起票したが `c858404` 反映前の観測に基づく**誤り**。実際は lint-web/typecheck-web ともに**緑**（`c858404` で `AuthSync.tsx` の `any` を型付け解消・`page.tsx`/`account/page.tsx` の `set-state-in-effect` は `eslint-disable` 済）。**make verify の真の赤は別件＝I-24（test-py）だった** |
| I-24 | **デモペルソナ不整合で test-py 赤（C0.1違反）** | ✅解消（2026-06-07） | `91d3282`「users.json を佐倉美咲に統一」が **users.json だけ**を変更し、backend（`keep_notes.json`・`canned.py`・`books/plans` ownerUid・Pythonテスト群・`run_pipeline`/`schemas`/`eval_harness`/`local_smoke` 既定ID）が `u_tadokoro`（田所・製造課長30名）のまま残り、**test-py が3件赤＝C0.1ゲート違反**（WBSの「58 passed」は当時から実態と乖離）。**2026-06-07：全面的に佐倉美咲（食品マーケ課長・7名・2026/04昇格・年上部下・初の評価面談・1on1負荷）へ再オーサリングして復旧**（`3e4b03b`）。検証＝test-py **60 passed,1 skipped**／lint／typecheck／make eval 全PASS／make pipeline 緑。make smoke は Windows の OpenSSL/POSIX 環境問題で本機未実行（本件と無関係）【WBS C0.1・2026-06-07】 |

---

## 審査での見せ方（プレゼン設計）

| # | 論点 | 状態 | メモ／出典 |
|---|---|---|---|
| P-1 | ばんくし氏に「必然性を数字で」示せるか | 🔴未解決 | A/B測定は将来検証。「どの著者版を選んだか」を学習シグナルとして数字化が代替【ARCH §12】 |
| P-2 | 限界の正直な開示（AIのみ執筆の品質限界） | 🟡方針OK | 「的中度と粒度で勝つ」と正面から語る【ARCH §12】 |
| P-3 | デモ動画尺・カット割り・提出フォーマット公式確認 | 🟡一部確認 | **【2026-06-05】提出先＝ProtoPedia 確定**（画像最大5枚／動画はYouTube URL貼付で埋め込み／ストーリー欄＝長文本体／システム構成欄は別枠）。**必須技術＝GEAP（旧Vertex AI）は"いずれか1つ以上"でよく、現状のVertex Gemini＋Cloud Runで充足**（Findy要件ページ実物確認）。残＝Findy公式の**動画の尺・形式の最終指定**（Notion要項・未取得）【構想 §10-4・Findy要項・P-6】 |
| P-4 | ピッチスライドの図解（自律アーキ／ループB将来構想） | 🟡役割分担済 | 詳細は別途【構想 §10-9】 |
| P-5 | STEP2のスコア閾値差し戻しループ＋調査サブの実データ取得をデモで必然性の画にする | 🟡方針OK・未実証 | デモ台本でカット化【ARCH §7】 |
| P-6 | **ProtoPedia作品ページの構成（ストーリー/画像5/システム構成/動画/各フィールド）** | 🟡ドラフト済 | 草案一式＝`publishr_other/Protopedia提出/`（`ストーリー欄_草案_v2.md`＝約4,000字・掴みは「自律フック→最大公約数の限界」の両建て／`画像プラン.md`＝体験3枚+必然性1+運用1+システム構成図／`投稿フォーム記入シート.md`＝全フィールド）。基準1〜5を各節に配置【構想 §10・MVP §6・WBS C6.7】 |
| P-7 | **体験画像は実フロントのスクショ（佐倉/7名）で撮る／図のクリーン公開版** | 🟡対応待ち | UIモック（`docs/ui/mockups`）は"30人"前提で佐倉(7名)と矛盾＝**最終画像は実フロントのスクショに差替前提**（モック自体は直さない）。図④⑤・システム構成図は内部値（閾値70/週15冊/100p/内部コード名）を含むため**公開版はマスク要**（保留中）。**公開クリーンリポ**（コード＋設計のみ・計画系除外）も提出までに用意【画像プラン.md・README 公開時運用・WBS C6.8】 |

---

## 将来検証・将来構想（今回は割り切る）

| # | 論点 | メモ／出典 |
|---|---|---|
| F-1 | お気に入り著者の混入比率・ランダム性のA/B再調整 | MVP=15%固定。サイクル2以降【AGENT §10-8・MVP §8】 |
| F-2 | Elasticsearch採否 | W5余力次第。外す前提でも可【ARCH §9/§12・MVP §8】 |
| F-3 | 攻めのスコープ候補（MVPスコープ §4-b の4件） | W2縦通し成功後に余力で判断【MVP §8】 |
| F-4 | 学習ループの実データ多サイクル | 「1サイクル回る」をデモで見せれば十分【ARCH §12】 |
| F-5 | AIだけの本に人が価値を感じ続けるか（事業の根本） | ハッカソンでは答えが出ず将来検証【ARCH §12】 |
| F-6 | ビジネス化（学習データ販売等） | プライバシーと緊張関係。ピッチ前面に出さない【構想 §11】 |
| F-7 | **GEAP④ Agent Runtime（旧Agent Engine）でエージェント実行** | ストレッチ（W5余力＆一瀬合意が前提）。⚠️**Agent Runtime は Cloud Scheduler/Pub-Sub/Eventarc トリガー非対応**＝モードAの自律トリガー(Scheduler)は Cloud Run 側に残す前提。現実解＝**4a ハイブリッド**（Scheduler→薄いCloud Run→企画会議ADKを Agent Runtime でホスト）／4b 観測のマネージドOAuth／4c 執筆。重さ中〜高（agents-cli/AdkApp化 or Vertex SDK・既存Cloud Run Job一部置換）。整理＝`publishr_other/GEAP活用_整理.md`【ADKスキル google-agents-cli-deploy】 |

---

## 最優先で潰す順序（TOP5）

1. ~~**友人MTGで役割・ADK実現性を握る**（G1-1）~~ ✅**完了（2026-06-05）**＝役割基本合意・ADK一旦これでいくで合意
2. **W1：ADK最小マルチエージェント疎通**（W1技術論点・最大の技術リスク）← 今すぐ
3. **W2：E2E縦通し1本**（プロジェクトの主要マイルストーン・ARCH §11 R3）
4. **デモ台本でスコア閾値の差し戻しカットを設計**（P-5／基準1を映す）
5. ~~Eval Set 8件＋サンプルDrive＋initialProfile選択肢（G1-9/G1-10・鉄田）~~ ✅**完了**（2026-06-04 initialProfile確定でクローズ）

---

## 決着済みログ（参考・蒸し返さない）

- ✅ **【友人MTG・2026-06-05 実施・完了】着手前の決定ゲートを全件クローズ**：①構想ピボット＝**新構想を正本にする方針を合意**／②役割分担＝**基本合意**（ただし基盤Firebase部分の担当は未定＝鉄田補助の可能性・後決め。Eval責務境界は I-21 どおり）／③技術フィージビリティ＝G1-1(ADK・一旦これでいく)・G1-13(Drive Picker＝フォルダ単位/Picker前提)・G1-14(3ソース疎通W1)・G1-3/5/6/7(連携)・I-19/I-9/I-20(データ詳細) を**全て確定**／④インフラ＝**GitHubを組織アカウント `cloud-dojo` へ移管→鉄田にオーナー権限付与（✅2026-06-05完了）→鉄田が App Hosting 連携(G1-7/B3.3)＋Cloud Build↔GitHub 接続(G1-18＝方式A) を実施（接続作業はW1/W4）**・G1-19(OAuth Production維持)・G1-15(通知FCM不要)を確定、**G1-17(Langfuseトレース実装方式)は判断不可で先送り（今後検証）**・G1-11(共有スキーマ正本＝packages/shared-schema、内容更新は鉄田引き継ぎ)を確定／⑤スケジュール＝週割り・ハード期日(6/30凍結・7/10提出)を合意／⑥デモ＝動画2本立てで合意。**①プロダクト紹介2.5分（ProtoPedia提出YouTube）を先に作る＝鉄田タスク継続。②60秒ピッチ内デモは最終選考通過後に作る想定で今は着手しない**。アジェンダ＝`publishr_other/meeting/20260604/MTGアジェンダ_20260604.md`。
- ✅ **【GEAP活用方針・2026-06-05】「Gemini Enterprise Agent Platform＝旧Vertex AI」と確認**＝必須要件（実行プロダクト×1＋AI技術×1）は現状の Cloud Run＋Vertex Gemini で**充足済**（Findy要件ページ実物確認・GEAPは"いずれか1つ以上"）。プラスアルファとして**②Gen AI Evaluation Service を品質ゲートに採用する方針**（自作judgeより軽い・基準5直球・I-21の実装ルート・動くコード済）。**④Agent Runtime はストレッチ**（Schedulerトリガー非対応の制約・F-7）。整理＝`publishr_other/GEAP活用_整理.md`・`GEAP②_EvalService具体化.md`。
- ✅ **【提出・2026-06-05】提出先＝ProtoPedia 確定＋作品ページ草案一式を作成**（ストーリー約4,000字・画像5＋システム構成図割当・全フィールド記入シート）＝`publishr_other/Protopedia提出/`（P-3/P-6/P-7・WBS C6.7/C6.8）。体験画像は実フロントのスクショ（佐倉/7名）に差替前提、図のクリーン公開版は保留。
- ✅ **【C3 鉄田巻取り完了・2026-06-06】C3.1/C3.4/C3.5 完了・C3全体担当を一瀬→鉄田へ変更**：**C3.1** Firestoreセキュリティルール本番デプロイ（`firestore.rules`/`firebase.json`/`.firebaserc`/`firestore.indexes.json` 生成・`firebase deploy --only firestore:rules` 実施・ownerUidモデル+`onlyChanged(['feedback'])`ヘルパー）✅ **C3.4** 観測ログサブコレクション(`users/{uid}/observations/{date}`)のセキュリティルール（C3.1に内包）✅ **C3.5** BFF FirestoreRepository実装（`apps/api/publishr_api/repositories/firestore_repository.py`・`firebase-admin>=6.5` 追加・`deps.py` DATA_SOURCE=firestore 切替・pytest 11件グリーン）✅。C4.9の②依存（Firestoreセキュリティルール）は解消済み。commit `b3fe6b7`/`ed8e0c3`。
- ✅ **【ABIU確認・C4.8本番デプロイ確認・2026-06-06】Firebase App Hosting 自動デプロイ動作確認**：CLI表示では「ABIU: Disabled」と誤表示されていたが Firebase Console 設定＞デプロイ画面で「自動ロールアウト: 有効✅」を確認。mainブランチへのpushで自動ビルド・ロールアウト稼働中。commit `23c022e`（feat(web): 読書UI大幅強化）が21:42に自動デプロイ完了済み。
- ✅ **【Firebase App Hosting 本番 live・2026-06-06】B3.3完了・mock公開中**（`publishr--publishr-498123.asia-east1.hosted.app`）。backend作成＋GitHub App連携完了。**Turbopack×npm workspaces問題の解消過程**：①root `package-lock.json` をgitignore→Turbopackが誤ってworkspace rootを検出する問題解消②root `package.json` の `workspaces` フィールドを削除（`npm ci` がroot lock fileを要求する問題解消）③`packages/shared-schema` をTurbopack root外から参照できない問題→`apps/web/src/lib/shared-schema/` にベンダーコピー＋tsconfig pathsを内向きに更新→build-010で成功。Netlify退役。
- ✅ **【フロント・2026-06-04／連携は2026-06-05 MTGで解除決定】ホスティング＝Firebase App Hosting／フロント＝Next.js(`apps/web`)で確定（G1-7・G1-11）**：`apphosting.yaml`(root=apps/web・mock公開)・mock本番ビルド緑は**main マージ済み**（commit `29d5d3e`／旧PR #2=new-concept-v2統合で取込済）。リージョン=`asia-east1`。連携ブロック解消→✅2026-06-06完了（上記参照）。Netlify退役。
- ✅ **【デモ環境・2026-06-04】デモ用Googleアカウント準備完了**：`publishr.demo.misa@gmail.com` 作成済。OAuth同意画面がProductionステータスのためテストユーザー登録不要（Productionでは100ユーザーまで誰でも認証可）。残＝録画直前のDriveデータ投入・calendar.icsインポート・Tasks手入力（W5）。
- ✅ **【鉄田単独タスク・2026-06-04】initialProfile選択肢確定(G1-9)**：5ステップ（業界13/職種11/役職7/関心19/読み口7）を実装。正本＝`apps/web/src/data/profileOptions.ts`（当初mockupに実装→G1-11でフロント正本を `apps/web` に確定・`apps/mockup/...` は参照コピー）。C4.1登録フォームの前提クリア。
- ✅ **【環境・2026-06-04】gcloud CLI×Norton 恒久対処完了(G1-20)**：W1のADK/デプロイでgcloud CLI利用可能（対処方式は `GCP環境構築ログ.md` 参照）。
- ✅ **【デモ・2026-06-04】カット割り（秒単位・C6.1旧案）を廃止→動画台本2本立てへ置換**：①プロダクト紹介2.5分(審査提出用)／②ピッチ内デモ60秒(体験オンリー)。台本アウトライン作成済（`publishr_other/demo/動画台本/`）。残＝録画(W5)。
- ✅ **【環境・2026-06-04】OAuth認証一式 完了**：同意画面を**Productionステータス**で設定（G1-19・refreshトークン長期有効化）・3スコープ・テストユーザー登録・OAuthクライアント`Publishr Web`発行・GitHub Secrets を **4本→6本**（GOOGLE_OAUTH_CLIENT_ID/_SECRET追加）。⚠️リダイレクトURIは仮`localhost:8080`のみ＝backendデプロイ後に本番URL追記（WBS B1.2）【GCP環境構築ログ.md】
- ✅ **【環境・2026-06-04】GCP IAM 2人招待・権限付与 完了**（ichisehiroshi@gmail.com）。Cloud Buildトリガーは**未接続**を実機確認（G1-18の前提＝旧タスク4完了）【GCP環境構築ログ.md】
- ✅ **【運用・2026-06-04】計画系docsをGitHub一本化**（wbs/open-issues/kickoff/roles＋master-schedule を `docs/planning/` に集約）。Drive＝デモ/ピッチのみ。公開時は計画系を外す前提（.gitignoreでは消えない＝新規公開リポにコピーが安全）【リポジトリ統合方針】
- ✅ **【v2再設計・2026-06-03】企画STEP2c＝調査3観点（A読者局面/B市場競合/Cテーマ知見）に再構成。コンセプト案・タスク分解サブは廃止。企画書フレーム8項目を先に固定し調査を逆算**【ARCH §7・AGENT §4】
- ✅ **【v2再設計】STEP3=著者キャスティング（編集者役・5人生成）／STEP4=新設 編集ループ（編集長⇄著者5人・プレビュー編集・1R・3観点採点）に分離。装丁はSTEP5へ**【AGENT §5・5-2】
- ✅ **【v2再設計】モードB＝本文編集ループ（編集長⇄著者・最高3R・弱い章のみ改稿）。改稿ループをStretchからINへ格上げ**【AGENT §7・MVP §4】
- ✅ **【IPO定義・2026-06-03】予約上限＝同時最大5冊（reserved+writing合計／I-16）。STEP1読者分析を Flash→Pro に格上げ。STEP0取得範囲＝Calendar/Tasks ±14日・生データのみ（G1-14）**【AGENT §2・§3・§9・API §3・MVP §5-2】
- ✅ **【IPO定義】ReaderProfile を3層構造（base＝保持／currentWork＝週次分析の主戦場・課題/局面/控える局面／readingBehavior＝既読被り回避・ハイライト・評価）。orgScaleは初回Driveから一度抽出しbase保持**【AGENT §3・ARCH §3】
- ✅ **【IPO定義】persona フレーム＝style を voiceStyle（文体軸）＋format（文章形式）に分割、persona本体はリッチに、5人を2軸で分散**【AGENT §5-3a】
- ✅ **【IPO定義】著者プレビュー BookDraft＝7フィールド（title/subtitle/今あなたは(deliveryReason)/解決する課題(problemToSolve)/核心メッセージ/アジェンダ/序文サンプル）＝書籍詳細モックアップ準拠**【AGENT §5-2a】
- ✅ **【IPO定義】本文ルーブリック5観点（I-12）・STEP2調査は3観点維持（A読者局面=STEP1起点のテーマ特化深掘り）**【AGENT §4-2c・§7】
- ✅ **【整合点検・2026-06-03】v2/IPO反映漏れを修正**：Firestoreルール favoriteAuthors を voiceStyle/format へ／`eval/eval_set.yaml` を3層Profile＋8項目plan＋0-100・4観点で再構築／`.env.example` に予約上限・編集ラウンド・dev/prodガード追加／`calendar.json` に attendeesCount/recurring 補強／UI仕様書 本詳細をBookDraft 7フィールド・予約上限5冊に整合。**新規 `../design/langfuse-tracing.md` 作成**（G1-17）【点検：A群5件＋B群起票】
- ✅ **【v2再設計】予約上限（旧：最大3冊）→ IPO定義で同時5冊に改定**【MVP §5-2・API §3】
- ✅ **【v2再設計】モデル＝ハイブリッド（担当者/リーダー/キャスティング/編集長/本文=Pro、STEP1/調査サブ/装丁=Flash、judge=Pro）**【AGENT §9】
- ✅ **【v2再設計】編集長を新設（執筆段階）。旧「編集長を独立させない」は“企画段階の選抜ゲートを1段にする”趣旨で、執筆段階の編集長とは両立**【AGENT §5-2・§7】
- ✅ 企画ステップ＝3階層の委任・評価構造（対立構造廃止）【2026-06-03】
- ✅ 著者＝テーマ確定時に都度生成5人（固定プール選抜廃止）【2026-06-03】
- ✅ スコア閾値ループ＝4観点×各25点・閾値70・最高3R・3R未達は最良案承認【2026-06-03】
- ✅ Evalは企画リーダーと同じ4観点共通ルーブリック・本命 総合<70で停止【2026-06-03】
- ✅ お気に入り著者の混入比率＝MVP15%【2026-06-03】
- ✅ 週3回・曜日別トリガー（土/水=本命・日=セレンディピティ）／読者分析は土朝の週1回【2026-06-03】
- ✅ 採番＝Firestore自動ID＋親子はフィールド【2026-06-02】
- ✅ textExcerpt＝1ファイル約4,000字・約10件【2026-06-02】
- ✅ インプット3ソース＝Drive＋Calendar＋Tasks【決定済】
- ✅ 選抜ゲート1段（編集長を独立させない）／著者版＝ユーザー選抜／STEP1は1体圧縮【決定済】
- ✅ 自律性の正体＝Cloud Scheduler／観測＝Langfuse Cloud（GKE不採用）／GCE不使用・Cloud Run完結【決定済】
- ✅ 本文ボリューム＝約100ページ【確定済】
- ✅ 週15冊の表紙生成＝MVP/デモは全冊先行生成、本番スケール時に「選択時生成」へ切替可能に設計【2026-06-03】
- ✅ GCPインフラ構築完了（Project ID: publishr-498123 / Firestore / Cloud Storage / Service Account / Secret Manager / Firebase Auth / Langfuse連携）【2026-06-03・infra/GCP環境構築ログ.md】
- ✅ OAuthトークン保存先＝Secret Manager（G1-5）【2026-06-03】
