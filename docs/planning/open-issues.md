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
| G1-3 | フロント⇔バック連携方式（Firestore直書き＋最小API） | ✅確定（MTG 2026-06-05）／**予約制廃止改定 2026-06-23で一部失効** | デフォルト案（Firestore直書き＋最小API）で異論なく確定。**【予約制廃止改定】「予約=POST /reserve の明示API」は失効＝予約制廃止により最小APIは3本→2本（OAuth／手動トリガー）。書庫保存はFirestore直書き**【AGENT §10-5/§11・API §6-2】 |
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
| G1-16 | **LLMコスト概算と上限ガード方針** | 🟡**2026-06-24 前提更新済／実測待ち** | `../design/cost-estimate.md` を予約制廃止後の前提に更新。コスト天井は旧「予約上限5冊」ではなく、**週3回×4冊＝週12冊の固定配本＋全冊本文生成**で管理する。prod guard も `PUBLISHR_MAX_BOOKS_PER_RUN=4` 前提へ修正。残＝Langfuse/GCP実測で実値上書き |
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
| I-1 | スコア閾値の最終値の運用調整 | 🟡仮置き70→**満点ドリフト是正(2026-06-23)** | 実データで調整。**2026-06-23：実Pro品質バッチで leader/eval_judge が96〜97の満点近辺へドリフトを確認→両者に同一文言のレンジ規律を追加（各観点25点=非の打ち所なし限定／総合90+は卓越例外／通常良作72〜88）。leader 実測89へ降下・high帯[70,100]維持で eval-safe・make eval 緑。最終運用調整は C5.4/5.5 で継続**【ADK §9-10・AGENT §10-7・I-37】 |
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
| I-16 | 予約上限の単位と執筆スロットル | ⛔**廃止（予約制廃止改定 2026-06-23）** | 旧: 同時最大5冊で確定（2026-06-03）＝reserved+writing 合計5冊以上で予約拒否。→ **予約制そのものを廃止**（配本バッチ内で全4冊を自動執筆）したため「予約上限」は失効。コスト天井は週3回×4冊＝週12冊に固定されることで担保（AGENT §7/§9）。残: 執筆並列度（1run内4冊の処理スロットル）は実装時に調整 |
| I-17 | セレンディピティの冊数 | ✅**2026-06-18 MTGで確定**／**保持は2026-06-24に再確認** | **日曜1セット（4冊）に決定**（旧暫定5冊→新4冊）。週3回×4冊/回=週12冊のうち、日曜の1回分（4冊）をセレンディピティセットとして提供。通常入荷（本命）は停止。週計: 本命8冊（2回×4冊）＋セレンディピティ4冊（1回×4冊）=12冊。**【2026-06-24確認】保持＝入荷から30日で棚落ち（`ARRIVAL_WINDOW_DAYS=30`）・書庫移動分のみ永久保存（I-29/AGENT §1）**【MTG 2026-06-18・3.2】 |
| I-18 | STEP4プレビュー編集ループの合格閾値 | 🟡仮置き→**編集calibration済(2026-06-23)** | **プレビュー＝総合50/75＋足切り10（仮置き）／本文＝総合70/100（仮置き）**。企画リーダー（70/100）より緩め。明らかな不足のみ1Rで弾く水準を実データで運用調整（C5.5）。**2026-06-23：実Proで4冊が25/25/24=74の同点・editorFeedback=null（編集のラバースタンプ化）を確認→step4_editor_preview を校正（満点アンカー外し・approveでも最弱観点feedback必須・合格例70→60）。合格閾値50は据え置き＝棚は空けない。実測で64〜66に点差＋全冊feedback化を確認**【AGENT §5-2b・§7・prompts step4_editor_preview/modeB_editor_body】 |
| I-19 | **ObservationBundle（観測ログ）の保存先コレクション** | ✅確定（MTG 2026-06-05）→クローズ | 推奨パッケージのまま異論なく確定＝**`users/{uid}/observations/{YYYY-MM-DD}` サブコレクション（日付docID＝冪等）に フル束をインライン保存・サーバ書込/本人read。生テキストのGCS分離・retention/TTLは将来F項目**。tech-arch §3／AGENT §2・付録／FIRESTORE §1・本文に match 追加／WBS C3.4 に反映【AGENT §2・FIRESTORE §1・ARCH §3】 |
| I-20 | **エラー/リトライ/冪等/タイムアウト方針** | ✅確定（MTG 2026-06-05）→クローズ | MVP最小方針のまま異論なく確定＝**①reserveは Firestore transaction で count確認→条件付き`draft→reserved` ②Pub/Sub冪等＝status が writing/published ならスキップ（bookId基準・messageId不要） ③モードA Job失敗＝ログ＋手動再実行（自動リトライなし） ④本文100pは章ごと分割保存で途中再開可＝Cloud Runタイムアウト上限内**。W1で dev最小構成の実行時間を実測【ADK §6・API §3】 |
| I-21 | **v2 Evalハーネスの再構築（LLM-judge化）** | 🔴未（一瀬・GEAP判定本体） | **【2026-06-06 裏取り更新】** `scripts/eval_harness.py`＋`apps/api/tests/test_eval_harness.py` は **v2整合済み・テスト緑**（commit `c06b143`「P0a mock回帰復旧 — eval_harness を v2 eval_set.yaml と整合」／`pytest tests/test_eval_harness.py`=2 passed）。現harnessは①**mock決定的回帰の床(H0a)**（`run_pipeline`＋`plan_relevance` 等は旧構想の残骸ではなく意図的に残す決定的チェック）＋②**v2 `eval/eval_set.yaml` の構造検証**（`load_eval_cases`/`validate_eval_set`・`cases` 8件=eval_01–08・`expectedBand`・`borderlineCases` 2件）を実装。**残＝Vertex Gen AI Eval Service（GEAP）による実 LLM-judge 採点ゲートの実装**（自作judgeでなくVertex接続＝一瀬）。**v2ハーネス（LLM-judge本体）＝`eval_set.yaml` を Gemini judge（`packages/prompts/eval_judge.md` と同一ルーブリック）で採点し、`cases`(8件・7/8でゲート)と `borderlineCases`(診断・C5.4/5.5)を読む** へ再構築。**Eval設計＝鉄田✅／ハーネス実装＝一瀬**。C5.1プロンプト実テスト・C5.3 CIゲート・C5.4再現性の前提。MTGアジェンダ §2。**【2026-06-05 実装ルート】v2ハーネスは Vertex AI Gen AI Evaluation Service（GEAP＝旧Vertex AI）で実装が有力**＝自作judgeより軽く、基準5の"純正運用"訴求に直結。動くコード＋設計＝対外資料 `publishr_other/GEAP②_EvalService具体化.md`（`from vertexai.evaluation import EvalTask, PointwiseMetric`／`metric_prompt_template`へ`eval_judge.md`移植／`CustomMetric`で構造化確実版／kind別ゲート 本命≥70+足切り/ずれ≤40/セレンディピティ30-60・8件中7/`borderlineCases`診断除外／CI差し替え・judge=Vertex Gemini Pro）【AGENT §8・eval_set.yaml 冒頭注記・WBS C5.3/C5.4・publishr_other/GEAP②】 |
| I-22 | **初回体験（first-run）の実15冊生成パイプライン未実装** | 🔴未（firestoreは空振り・C1依存） | 登録直後の「空→生成中→15冊」初回体験は**mockでは決定的15冊（本命10＋セレンディピティ5・`apps/web/src/data/firstRunCatalog.ts`）の時間差入荷で動作**（`runFirstRun`・生成中UI・2026-06-07）。**firestoreモードは`runFirstRun`→`/api/trigger/planning`を叩くだけで実15冊をFirestoreに書く処理が無い**ため生成中UIが空振り→45秒安全タイムアウト/手動「書店を見る」で空書店へ抜ける（詰まりはしない）。実生成は**C1.1–C1.6（モードA全STEP）＋初回まとめ生成のAPI/Job**に依存。デモはmockサンドボックスで見せる前提【WBS C4.2/C1・2026-06-07】 |
| I-23 | **lint（make verify の lint-web）** | ✅緑（誤認訂正・2026-06-07） | 当初「赤」と起票したが `c858404` 反映前の観測に基づく**誤り**。実際は lint-web/typecheck-web ともに**緑**（`c858404` で `AuthSync.tsx` の `any` を型付け解消・`page.tsx`/`account/page.tsx` の `set-state-in-effect` は `eslint-disable` 済）。**make verify の真の赤は別件＝I-24（test-py）だった** |
| I-24 | **デモペルソナ不整合で test-py 赤（C0.1違反）** | ✅解消（2026-06-07） | `91d3282`「users.json を佐倉美咲に統一」が **users.json だけ**を変更し、backend（`keep_notes.json`・`canned.py`・`books/plans` ownerUid・Pythonテスト群・`run_pipeline`/`schemas`/`eval_harness`/`local_smoke` 既定ID）が `u_tadokoro`（田所・製造課長30名）のまま残り、**test-py が3件赤＝C0.1ゲート違反**（WBSの「58 passed」は当時から実態と乖離）。**2026-06-07：全面的に佐倉美咲（食品マーケ課長・7名・2026/04昇格・年上部下・初の評価面談・1on1負荷）へ再オーサリングして復旧**（`3e4b03b`）。検証＝test-py **60 passed,1 skipped**／lint／typecheck／make eval 全PASS／make pipeline 緑。make smoke は Windows の OpenSSL/POSIX 環境問題で本機未実行（本件と無関係）【WBS C0.1・2026-06-07】 |
| I-25 | **serendipity 採点の較正（読み替え①の安定性・境界帯）** | 🟡方針確定・実LLM未検証（要MTG共有） | STEP2手動検証（2026-06-12）で、leader/eval_judge の①relevance を serendipity時に「嗜好・許容度との整合」へ読み替える方針を確定（中レンジ30-60を廃止しモノサシ統一・`1bfc2ac`／一瀬合意済み）。**ただし AI Studio 実測で同一企画群の①が大きく振れた**（条項なし8→あり23・形式不備R1=8→修正R2=23）。few-shot錨（leaderにserendipity採点例1件追加）で緩和したが、**70点近傍の serendipity 企画を安定して裁けるかは未検証**。C5.4 実judge再現性（一瀬・`make eval-repro`）に serendipity ケースを含めて σ/CV を実測し、閾値運用（C5.5）で詰める。関連 G1-8/I-1/I-18/I-21【packages/prompts/{step2_plan_leader,eval_judge}.md・2026-06-12】 |
| I-26 | **findings 書誌の実在性担保（外部API照合・groundingURL永続化）** | 🟡規律で緩和済・恒久対処は将来 | STEP2c-B/C で findings の著者名・監修者・URL/ISBN を**モデル記憶から創作する**事例を複数観測（三田: 共著者捏造／佐倉serendipity: ページID・ISBN創作）。プロンプトに実在性規律（検索取得ページのみ転記・URL組み立て禁止・確認不能は落とす）を追加し`1d27f87`で捏造ゼロを3ラン連続達成。**ただしモデルの自己申告依存＝ゼロ保証ではない**。本格運用は書誌の外部API照合（国会図書館/Google Books等）が要る。併せて grounding が返す `vertexaisearch.../grounding-api-redirect/...` URLは**有効期限ありで証跡が将来切れる**ため、保存時に正規URLへ解決する処理が要る。**2026-06-23：実Pro実測でこのリダイレクトURL形式を再確認（1run 24URL）＝人手照合しづらく将来失効する課題は継続。併せて subMarket で著者欄に出版社名混入（翔泳社/セルバ出版）を観測→B規律に「authorは著者名のみ・出版社/レーベル代用禁止・確認不能は省略」＋「コードフェンスで囲わずJSON本体のみ」を追加（step2_research_subs B節）**【AGENT §4-2c・2026-06-12・2026-06-23】 |
| I-27 | **serendipity テーマ選定の個人化（全読者共通ハードコード）** | 🔴未（ハッカソン後スコープ） | `deterministic.py` `_serendipity_theme` は全読者共通の固定文字列（`1695fe2` で距離2文言「興亡の歴史」に更新）。本来は読者ごとに「関心の隣」を導出すべき（例: 佐倉の drv_007 パーパス関心→ブランドの文化史/記号論）。距離2の設計原則「テーマに challenges 語彙（能力名詞）を含めず主語を素材側に置く」は個人化プロンプトを書く際の規律として持ち込む。デモは固定文字列で成立するため割り切り【deterministic.py docstring・2026-06-12】 |
| I-28 | **PlanProposal に「形式」フィールドがない（受容リスクへの応答が構造化されない）** | 🟡将来・スキーマ拡張候補 | serendipity 検証で leader が「読書体力（多忙・要点絞り希望）に対し重厚な章立てでは挫折する」と差し戻し→owner が対話形式/読み切り/分量を**タイトル・diffFromMarket・agendaOutline に埋め込んで**回避（R2承認）。回避は効くが、本の形式（分量・語り口・構成）を表す独立フィールドがないため形式要求の入出力が曖昧。スキーマに `format`/`lengthHint` 等を足すか現状の埋め込みで割り切るかは要判断。honmei の受容性（積読対策）にも効く論点【packages/shared-schema agent_io・2026-06-12】 |
| I-29 | **入荷保持期間・棚落ち＋書庫の仕組み** | ✅**実装済（2026-06-24）**／実Cloud Run確認残 | ~~MTG 2026-06-18: 7日→過去4週間（28日）・最大48冊~~ → **【2026-06-24確認】保持＝入荷から30日で棚落ち（`ARRIVAL_WINDOW_DAYS=30`）。書庫へ移した本（`books/{bookId}.archivedAt` セット）だけ永久保存し、未保存は30日経過で入荷一覧から消滅**。実装＝フロント `apps/web/src/lib/arrival.ts` は `ARRIVAL_WINDOW_DAYS=30`、入荷一覧フィルタは「`createdAt+30日 > now` かつ `archivedAt` なし」、書庫ページは `archivedAt` ありも表示。物理削除バッチは任意【AGENT §1/§11・arrival.ts】 |
| I-30 | **動的フィルタリング（書庫移動後の入荷一覧非表示）** | ✅**実装済（2026-06-24）** | 書庫保存は `books/{bookId}.archivedAt` をセットし、書店トップは `isVisibleArrival()` で「30日以内かつ未保存」の本だけ表示する。書庫ページは `archivedAt` あり、または `shelf=library` の本を表示する。`mock`/`firestore`/`bff` provider に `saveToLibrary` を追加し、Firestore rules は本人の `archivedAt` 更新を許可【MTG 2026-06-18・3.2・arrival.ts・provider.ts・firestore.rules】 |
| I-31 | **デモ用即時入荷トリガーボタン** | ✅**実装済（2026-06-24）** | アカウント画面に `mock` では非表示のデモ用「今すぐ入荷を実行」ボタンを追加。`bff` は `POST /api/trigger/planning` 実行後に本一覧を再読込、`firestore` は既存 API 呼び出し＋Firestore購読で反映。既存のmock書店・初回体験（`runFirstRun`）には触れない実装にした。残＝実Cloud Run/Firestore環境でのブラウザ確認【MTG 2026-06-18・3.3・G1-6】 |
| I-32 | **デモ環境ID/Password認証** | 🔜検討中（2026-06-18 MTG決定） | **MTG 2026-06-18 で方針確定**。デモ環境への認証として ID/Password 方式を実装。将来的には Google認証等のアイデンティティプロバイダ連携を継続検討。現状は Firebase Auth によるGoogle認証のみ。MVP/ハッカソン提出までにBasic認証または別途ID/Password保護レイヤーを追加するか要判断【MTG 2026-06-18・3.3】 |
| I-33 | **著者お気に入り（favoriteAuthors）状態保持バグ（優先度: 高）** | ✅**実装済（2026-06-24）** | `favoriteAuthors` を Firestore `users/{uid}.favoriteAuthors` から購読して `useFavorites()` に反映。削除は `personaId` で既存配列を探し、Firestore上の実オブジェクトを `arrayRemove` する。保存エントリには schema 必須の `voiceStyle` / `format` を補完し、読了ページのお気に入りボタンも実保存へ接続【MTG 2026-06-18・WBS C4.6・favorites-store.ts・user-writes.ts】 |
| I-34 | **GitHub公開用新規パブリックリポジトリ作成（PII除去・履歴クリーン）** | 🔜着手前（2026-06-18 MTG決定） | **MTG 2026-06-18 で方針確定**。既存リポ（`cloud-dojo/publishr`）には PII（個人を特定できる情報）や内部ドキュメントの履歴が蓄積されており、完全なスクラブは技術的整合性の観点から困難と判断。方針: 現行リポを**「開発・プライベート用」として隔離保持**し、外部公開・本番用として**履歴クリーンな新規パブリックリポジトリを別途作成**する（コードと docs/design のみコピー・計画系 docs は除外）。WBS C6.6/C6.5 の公開クリーンリポ作業と統合【MTG 2026-06-18・3.4・WBS C6.6】 |
| I-35 | **本文生成ボリュームのパラメータ化（3000文字以上への拡張）** | 🔜実装待ち（2026-06-18 MTG決定） | **MTG 2026-06-18 で確定**。現行の `body_pages_min=3, body_pages_max=5`（約3000文字）から、章立てに応じた最適な文字数へ拡張する。実装方法: プロンプト引数のパラメータ化（Parameterization）によりプログラム側から動的に生成ボリュームを制御。`config.py` の `body_pages_min/max` または新パラメータ `BODY_CHAR_TARGET` を追加し、プロンプトテンプレートに `{{target_chars}}` 等で注入する方式を検討【MTG 2026-06-18・3.1・apps/api/publishr_api/config.py】 |
| I-36 | **調査サブの拒否デレール＋リーダー入出力整合** | ✅修正(2026-06-23) | 実Proバッチで調査サブC(`subThemeInsight`)がADKキックオフ文「今朝の企画会議を始めてください」に釣られ「会議は始められない」と全面辞退→調査トリオ1本が無言で死亡（入力が`{{tentativeTheme}}`のみで文脈が薄く合図文に引っ張られるのが原因）。step2_research_subs C節に拒否ガード（合図文は調査開始トリガー・辞退/前置き禁止・JSONのみ）を追加。併せて **plan_leader の③researchUse 基準が `subThemeInsight` を採点根拠に挙げるのに入力テンプレ(`_LEADER_INPUTS`)へ未注入**の不整合を発見→`{{subThemeInsight}}` を注入＋「調査サブが空/拒否/一般論なら③足切り→revise」規律を追加（調査欠落を素通りさせない）。実Proで辞退消滅を確認【planning/vertex_agent.py・step2_{research_subs,plan_leader}.md・2026-06-23】 |
| I-37 | **実LLM品質バッチハーネス（手貼り廃止）** | ✅整備(2026-06-23) | プロンプト品質ループを手貼りから自動化＝`scripts/run_aistudio_batch.py`（STEP0→1→2→3→4 一気通貫・各STEP出力＋引用URL照合リストを `publishr_other/aistudio_runs/` へ）。`--backend vertex`(既定・ADC/publishr-498123)/`aistudio`(GOOGLE_API_KEY) 切替・`--cheap`(全工程flash)・`--reader-llm real`。Windows企業TLS対応(SSLKEYLOGFILE除去＋truststore)内蔵。**C5.1 プロンプト実テストの実働ツール**。AI Studioキーは前払い残高0で429になり Vertex 経路が低摩擦【scripts/run_aistudio_batch.py・memory publishr-aistudio-batch・2026-06-23】 |

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

- ✅ **【予約制廃止改定・2026-06-23／保持期間再確認・2026-06-24】配本モデルを大改定**：①**配本＝4テーマ・各1冊（1-1-1-1・週3回×4冊＝週12冊）**②**予約制（モードA/B区別・モードB後追い執筆・`POST /reserve`・同時上限5冊・Pub/Sub執筆発火）を廃止**＝各配本runで**全4冊を予約を待たず本文まで作り切って published**③**棚＝入荷から30日で棚落ち（消滅・`ARRIVAL_WINDOW_DAYS=30`）、書庫へ移した本だけ永久保存**。docs反映済＝AGENT §1/§7/§9/§11・wbs C1/C2・open-issues I-16(廃止)/I-17/G1-3/G1-16。**⚠️要交通整理＝既実装の予約フロー（C2.1-2.3 mock・C4.4 予約UI・M3達成分）と旧3テーマ配線（未コミットの state_keys/provider/__init__・agent_io の PlanSet系）は本改定で要見直し**【AGENT §1・wbs C1/C2】
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
- ✅ **【serendipity採点・2026-06-12】中レンジ帯(30-60)を廃止しモノサシ統一**＝serendipity も閾値70。①relevance を serendipity時に「業務直撃」でなく「嗜好・許容度（readingGenres/readingBehavior/serendipityTolerance）との整合」へ**読み替え**て同一閾値で裁く。旧設計（serendipityは構造的に低得点で別帯）だと leader の閾値70を満たせず**毎回3R強制承認**になる構造問題があったため。leader/eval_judge/eval_set.yaml/eval_gate を一括統一（`1bfc2ac`・一瀬合意済み）。残較正は I-25【2026-06-12】
- ✅ **【品質バッチ・判定役校正 2026-06-23】実Pro品質バッチ(`scripts/run_aistudio_batch.py`)で u_mita を実測し6件修正＝①調査拒否ガード ②leader入出力整合＋調査欠落足切り ③subMarket書誌規律(著者≠出版社・フェンス除去) ④Cドメイン錨 ⑤編集calibration(満点同点→点差＋feedback) ⑥leader+eval_judge満点ドリフト是正。判定役3役(編集/leader/eval_judge)の満点連発を是正しモノサシ統一。`make eval`緑・pytest緑・実Pro検証済。詳細は I-36/I-37/I-1/I-18/I-26【2026-06-23】
- ✅ お気に入り著者の混入比率＝MVP15%【2026-06-03】
- ~~✅ 週3回・曜日別トリガー（土/水=本命・日=セレンディピティ）／読者分析は土朝の週1回【2026-06-03】~~ → **【2026-06-18 MTG改定】** 週3回×4冊/回=週12冊（本命2回×4冊=8冊＋日曜セレンディピティ1回×4冊=4冊）。 ~~保持4週間・最大48冊~~ → **【2026-06-24確認】保持＝入荷から30日で棚落ち（`ARRIVAL_WINDOW_DAYS=30`）・書庫移動分のみ永久保存**（I-17/I-29更新）
- ✅ 採番＝Firestore自動ID＋親子はフィールド【2026-06-02】
- ✅ textExcerpt＝1ファイル約4,000字・約10件【2026-06-02】
- ✅ インプット3ソース＝Drive＋Calendar＋Tasks【決定済】
- ✅ 選抜ゲート1段（編集長を独立させない）／著者版＝ユーザー選抜／STEP1は1体圧縮【決定済】
- ✅ 自律性の正体＝Cloud Scheduler／観測＝Langfuse Cloud（GKE不採用）／GCE不使用・Cloud Run完結【決定済】
- ✅ 本文ボリューム＝約100ページ【確定済】
- ~~✅ 週15冊の表紙生成＝MVP/デモは全冊先行生成【2026-06-03】~~ → **【2026-06-18 MTG改定】** 週12冊（4冊×3回: 本命2回+セレンディピティ1回）=週12冊。 ~~4週保持48冊~~ → **【2026-06-24確認】30日棚落ち＋書庫永久（I-29）。表紙含め全冊先行生成方針は維持＝予約を待たず本文まで作り切る**
- ✅ GCPインフラ構築完了（Project ID: publishr-498123 / Firestore / Cloud Storage / Service Account / Secret Manager / Firebase Auth / Langfuse連携）【2026-06-03・infra/GCP環境構築ログ.md】
- ✅ OAuthトークン保存先＝Secret Manager（G1-5）【2026-06-03】
