# Publishr 未決論点台帳

> **役割**: 各設計ドキュメントに散在していた「未確定／未決／友人MTGで詰める」論点を1枚に集約した台帳。各docの未確定セクションはここを参照する。
> **凡例**: 🔴未決 ／ 🟡方針あり・要確認 ／ ✅決着（下部のログ参照）。各論点に【出典】を付す。
> **前提**: PatentSentinel（代替案）は不採用。**撤退はしない＝Publishrをやりきる**前提のため、撤退基準・採用GO判断の論点は持たない。
> **全体の目次は [正本マップ](../README.md)。**
> **🧭 現在地（2026-06-04）**: 環境系の論点（OAuth保存先G1-5・GCP構築・Secrets）は決着。**鉄田単独の先行タスクも完了**＝G1-9(initialProfile)✅・G1-20(gcloud×Norton)✅・G1-10(Eval実データ)方針確定済。デモはカット割り廃止→動画台本2本立てへ置換✅。**残る決定ゲートは友人MTG（明日夕方予定）のみ**＝ここで G1-1(ADK実現性)／G1-2(役割)／**G1-13(Drive Picker・最重要)**／G1-15(通知)／G1-18(Cloud Build方式)／G1-19(OAuth公開) を握ればW1着手可。

---

## 着手前に「決める」論点（友人MTGで潰す）

| # | 論点 | 状態 | 決め方／出典 |
|---|---|---|---|
| G1-1 | ADK実現可能性の握り（W1 Hello Worldの範囲） | 🔴未 | 友人MTG【ARCH §12・ADK §9】 |
| G1-2 | 役割分担（友人＝エージェント／鉄田＝フロント） | 🟡方針あり | 友人MTGで最終合意【ARCH §5】 |
| G1-3 | フロント⇔バック連携方式（Firestore直書き＋最小API3本） | 🟡デフォルト案確定 | 予約のPub/Sub発火を明示API（POST /reserve）で行うか・Firestoreトリガーか。本線＝明示API【AGENT §10-5/§11・API §6-2】 |
| G1-4 | `ownerUid` フィールド方式 vs サブコレクションネスト | 🟡ownerUid方式で原典反映済 | ネストに覆す場合は要再変更【FIRESTORE §2/§5-1・API §6-5】 |
| G1-5 | OAuthトークンの保存先（Secret Manager か Firestore暗号化） | ✅決着 | **Secret Manager で確定**（infra/GCP環境構築ログ.md・Langfuseキー登録済み・2026-06-03）【API §6-1】 |
| G1-6 | 手動トリガーの認可範囲（デモ垢限定か全ユーザー可か） | 🔴未 | コスト暴走防止【API §6-3】 |
| G1-7 | フロント本番ホスティング／APIベースパス／CORS | 🟡ホスティング決着・連携ブロック中 | **ホスティング＝Firebase App Hosting で確定（フロント＝`apps/web`/Next.js＝G1-11も解消・2026-06-04）**。`apps/web/apphosting.yaml`(root=apps/web・`NEXT_PUBLIC_DATA_SOURCE=mock`)・mock本番ビルド緑・**PR #2** 準備済。リージョン=`asia-east1`(Tokyo無のため)。**🔴ブロック＝App Hosting の GitHub App 連携はリポ所有者(一瀬)のみ可**（鉄田はcollaboratorで不可・G1-18と同種の所有者依存）。→ **一瀬が backend 作成 or GitHub App 許可で解除**（明日MTG／WBS 0.8）。CORS・ベースパスは引き続き友人MTG【API §6-4・CICD §3】 |
| G1-8 | 企画リーダーのスコア閾値・満点定義 | 🟡仮置き70/100 | MVPは4観点×各25点・閾値70。運用調整【AGENT §10-7・ADK §9-10・MVP §8】 |
| G1-9 | initialProfile 選択肢リスト（業界/職種/役職/関心/読書傾向） | ✅決着 | **2026-06-04確定**＝5ステップ（業界13/職種11/役職7/関心19/読み口7）を `apps/mockup/src/data/profileOptions.ts` に実装。叩き台 `API契約仕様.md` §2-a 準拠【MVP §8】 |
| G1-10 | Eval Set 8件の実データ作成 | 🔴未（鉄田） | 方針確定・素材作成のみ残【MVP §8】 |
| G1-11 | フロントUIテンプレ／ライブラリ選定 | 🟡フレームワーク決着・スキーマ正本残 | **フロント＝Next.js（`apps/web`）で確定（2026-06-04）**。モックアップ（`apps/mockup`/Vite）はデザイン参照専用に降格。**併せて front/back 共有スキーマの正本の置き場所（Pydantic/TS/JSON Schemaのどれを単一ソースにし、モノレポのどこに置くか）をW1 scaffold時に確定＝型ドリフト防止**（型SOT＝`@publishr/shared-schema`で運用中）【ARCH §12・本台帳B7由来】 |
| G1-12 | サンプルDrive準備 | ✅完了 | 佐倉美咲ペルソナで Drive10/Calendar28/Tasks15 整備済（2026-06-02）。デモ再現性の要【ARCH §12】 |
| G1-13 | **drive.file のファイル選択方式（Google Picker 連携）** | 🔴未 | `drive.file` はアプリがDrive内を走査・一覧**できない**（ユーザーが選んだファイルのみ）。`connectedSources.drive.folderIds[]` の取得は **Google Picker API** 前提で確定する必要。選択粒度（ファイル/フォルダ）と保持方法も。後出しは登録フロー作り直し＝最重要。友人MTG【ARCH §3/§6-5・API §2-a/§4】 |
| G1-14 | STEP0でCalendar/Tasksを消費する仕様 | ✅確定（取得範囲）／🟡grounding課金残 | **取得範囲＝±14日（過去2週＋先2週）・生データのみ（要約しない）で確定（2026-06-03）**。Calendar/Tasksは確定インプットへ格上げ済（AGENT §2／ARCH §1・§3整合済）。STEP1 currentWork（局面・課題・upcomingKeyEvents）へ反映。**残＝調査サブB/CのGoogle検索grounding課金影響は友人MTGで確認**【AGENT §2・MVP §3 #1】 |
| G1-15 | **入荷/執筆完了の通知方式** | 🟡推奨デフォルトあり | デモ カット3「入荷通知」・カット5「予告通知」が依存。**MVP=アプリ内 Firestore購読＋トースト/バナーで十分（FCMプッシュ不要）**。これを明記しFCM工数化を防ぐ。友人MTGで最終確認【デモシナリオ カット3/5・UI 3-8】 |
| G1-16 | **LLMコスト概算と上限ガード方針** | 🟡ドラフト済 | `../design/cost-estimate.md` 作成済（ハイブリッド＋予約上限5冊＋編集ループ）。dev/prodガードは `.env.example` に追加済（BODY_PAGE_COUNT/ENABLE_IMAGEN/BATCH_BOOKS_OVERRIDE）。残＝W1実測で実値上書き |
| G1-17 | **Langfuseトレース仕様（必然性の証跡）** | 🟡ドラフト済 | `../design/langfuse-tracing.md` 作成済（企画スコアループ・編集ループ2系統・調査groundingの取得URLをspan属性で残す）。**実装方式（OTel経由 or Langfuse SDK直）・grounding取得元フィールドを友人MTG／W1疎通で確定**。実装は友人・W4【CICD §5】 |
| G1-20 | **gcloud CLI×Norton のHTTPS検査でCLIが通らない** | ✅決着 | **2026-06-04 恒久対処完了**（W1のADK/デプロイでgcloud CLIが利用可能に）。※対処方式の詳細は `GCP環境構築ログ.md` に追記のこと【GCP環境構築ログ.md 2026-06-04】 |
| G1-18 | **Cloud Build↔GitHub接続方式（A:所有者がGitHub App接続 ／ B:Actionsから `gcloud builds submit` で常時接続を省略）** | 🟡推奨B | リポ `hiroshiichise/publishr` は**個人アカウント所有**で、GitHub App認可は**所有者(一瀬)のみ**可。鉄田のGitHub Secrets登録はコラボレーター権限で可能と実機確認済（2026-06-04・4本登録済）。Cloud Buildトリガーは現状**未接続**を確認済（タスク4=完了）。**推奨＝B（所有者依存を避け最小構成・Actions主導フローと整合）**。AかBを**友人MTGで確定**。実装はW4【CICD §3・GCP環境構築ログ.md 2026-06-04】 |
| G1-19 | **OAuth同意画面の公開ステータス（Testing vs Production未審査）** | 🟡推奨Production | **Testingモードはリフレッシュトークンが7日で失効**→週次自律バッチ（Cloud Scheduler×Secret Manager保存トークン）が1週間後に停止しPublishrの自律性が壊れる。**Production(未審査)ならトークン長期有効**（未審査警告はバイパス可・100ユーザー上限）。現状はProductionに設定済（2026-06-04）。**推奨＝Production維持**。OAuth実装担当=友人につき**MTGで握る**【G1-5・API §6-1・GCP環境構築ログ.md 2026-06-04】 |

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
| I-5 | initialProfile の変更可否 | 🟡MVPは変更不可 | 次サイクルのDrive観測で profile 自然更新。将来は設定画面【API §6-6】 |
| I-6 | initialProfile 書込制限の実装（初回のみcreate） | 🟡方針あり | ルールの affectedKeys で表現。細部は友人MTG【FIRESTORE §5-5】 |
| I-7 | favoriteAuthors の上限件数 | 🟡MVP10件上限 | 超過は古いものから削除 or UI制限【API §6-7】 |
| I-8 | favoriteAuthors の参照方式 | 🟡コピー保持推奨 | name/style をコピーしorphan防止【FIRESTORE §5-6】 |
| I-9 | 読書ログの置き場所（feedback集約 か logs/サブコレクション） | 🔴未 | 集約ならルール単純【FIRESTORE §5-2】 |
| I-10 | 本文(GCS)の保護（署名付きURL/IAM） | 🟡優先度中 | Firestoreルール範囲外。提出リポジトリに残すなら明記【FIRESTORE §5-3】 |
| I-11 | personas 読み取りを全認証ユーザーに開放してよいか | 🟡MVPは可 | 商用化時に再検討【FIRESTORE §5-4】 |
| I-12 | 編集長の本文ルーブリック（執筆品質の採点観点） | ✅確定 | **5観点で確定（2026-06-03）**：①構成の一貫性 ②各章の掴み（引き込み） ③読者状況への的中 ④著者ペルソナの一貫性 ⑤実践性・具体性（行動に落ちる・水増し検出）【AGENT §7】 |
| I-13 | 実在著者モデル参照の知財リスク | 🟡架空化方針 | 実在著者は作風参考に留め、名前・経歴は架空。規約の知財条項も要確認【構想 §10-11・ARCH §12】 |
| I-14 | デモのデータ戦略（ライブ生成 vs seed再生） | 🔴未 | LLM出力は非決定的。録画再現性のため「seed投入＋必要箇所だけライブ」を想定。fixtures→Firestore/GCS のseed投入機構を作るか判断。W5録画直前の事故回避【MVP §5-1・デモシナリオ】 |
| I-15 | Firestore複合インデックス／クエリ形状の早期確定 | 🔴未 | 棚・書庫クエリ（ownerUid×status×themeKind×createdAt降順・favorite等）は複合インデックス必須。クエリ形状を早めに列挙し `firestore.indexes.json` を用意（Terraformにも乗せる）。後出しは実行時エラーで露見【API §1・ARCH §3】 |
| I-16 | 予約上限の単位と執筆スロットル | ✅確定（単位）／🟡スロットル残 | **同時最大5冊で確定（2026-06-03）**＝reserved+writing の合計が5冊以上で予約拒否（API §3）。執筆並列度（1日1冊等の処理スロットル）は実装時に調整【MVP §5-2・API §3】 |
| I-17 | セレンディピティの冊数（5冊 or 3冊） | 🟡暫定5冊維持 | 暫定は本命5＋セレンディピティ5＝週15冊。3冊に絞ると週13冊。デモ・コスト・物語のバランスで判断【MVP §5-2】 |
| I-18 | STEP4プレビュー編集ループの合格閾値 | 🔴未（v2） | 企画リーダー（70）より緩め。明らかな不足のみ1Rで弾く水準を運用で調整【AGENT §5-2b】 |
| I-19 | **ObservationBundle（観測ログ）の保存先コレクション** | 🔴未 | データモデルは plans/books/personas/users のみ。STEP0出力の保存先が未定義＝直書きできない。推奨: `observationLogs/{uid}/{date}`（監査ログ型）or users配下サブコレクション。決定後 Firestoreルール §1表・本文に match 追加【AGENT §2・FIRESTORE §1・ARCH §3】 |
| I-20 | **エラー/リトライ/冪等/タイムアウト方針** | 🔴未 | モードA Job失敗のログ/再実行・Pub/Sub再配信の冪等キー（messageId or bookId）・reserveの順序性（Firestore transactionでcount確認→条件付き更新）・本文100p+編集ループのCloud Runタイムアウト。MVPは最小方針でよいが着手前に方針だけ。W1で dev最小構成の実行時間を実測【ADK §6・API §3】 |

---

## 審査での見せ方（プレゼン設計）

| # | 論点 | 状態 | メモ／出典 |
|---|---|---|---|
| P-1 | ばんくし氏に「必然性を数字で」示せるか | 🔴未解決 | A/B測定は将来検証。「どの著者版を選んだか」を学習シグナルとして数字化が代替【ARCH §12】 |
| P-2 | 限界の正直な開示（AIのみ執筆の品質限界） | 🟡方針OK | 「的中度と粒度で勝つ」と正面から語る【ARCH §12】 |
| P-3 | デモ動画尺・カット割り・提出フォーマット公式確認 | 🔴未 | 【構想 §10-4】 |
| P-4 | ピッチスライドの図解（自律アーキ／ループB将来構想） | 🟡役割分担済 | 詳細は別途【構想 §10-9】 |
| P-5 | STEP2のスコア閾値差し戻しループ＋調査サブの実データ取得をデモで必然性の画にする | 🟡方針OK・未実証 | デモ台本でカット化【ARCH §7】 |

---

## 将来検証・将来構想（今回は割り切る）

| # | 論点 | メモ／出典 |
|---|---|---|
| F-1 | お気に入り著者の混入比率・ランダム性のA/B再調整 | MVP=15%固定。サイクル2以降【AGENT §10-8・MVP §8】 |
| F-2 | Elasticsearch採否 | W6余力次第。外す前提でも可【ARCH §9/§12・MVP §8】 |
| F-3 | 攻めのスコープ候補（MVPスコープ §4-b の4件） | W2縦通し成功後に余力で判断【MVP §8】 |
| F-4 | 学習ループの実データ多サイクル | 「1サイクル回る」をデモで見せれば十分【ARCH §12】 |
| F-5 | AIだけの本に人が価値を感じ続けるか（事業の根本） | ハッカソンでは答えが出ず将来検証【ARCH §12】 |
| F-6 | ビジネス化（学習データ販売等） | プライバシーと緊張関係。ピッチ前面に出さない【構想 §11】 |

---

## 最優先で潰す順序（TOP5）

1. **友人MTGで役割・ADK実現性を握る**（G1-1）← 今すぐ
2. **W1：ADK最小マルチエージェント疎通**（W1技術論点・最大の技術リスク）
3. **W2：E2E縦通し1本**（プロジェクトの主要マイルストーン・ARCH §11 R3）
4. **デモ台本でスコア閾値の差し戻しカットを設計**（P-5／基準1を映す）
5. ~~Eval Set 8件＋サンプルDrive＋initialProfile選択肢（G1-9/G1-10・鉄田）~~ ✅**完了**（2026-06-04 initialProfile確定でクローズ）

---

## 決着済みログ（参考・蒸し返さない）

- 🟡 **【フロント・2026-06-04】ホスティング＝Firebase App Hosting／フロント＝Next.js(`apps/web`)で確定（G1-7・G1-11）**：`apphosting.yaml`(root=apps/web・mock公開)・mock本番ビルド緑・**PR #2** 準備済。リージョン=`asia-east1`。**残ブロック＝App Hosting の GitHub App 連携はリポ所有者(一瀬)のみ可**（鉄田collaborator不可）→ 一瀬が backend 作成 or GitHub App 許可で解除（明日MTG／WBS 0.8）。Netlify は App Hosting 安定後に退役。
- ✅ **【デモ環境・2026-06-04】デモ用Googleアカウント準備完了**：`publishr.demo.misa@gmail.com` 作成済。OAuth同意画面がProductionステータスのためテストユーザー登録不要（Productionでは100ユーザーまで誰でも認証可）。残＝録画直前のDriveデータ投入・calendar.icsインポート・Tasks手入力（W5）。
- ✅ **【鉄田単独タスク・2026-06-04】initialProfile選択肢確定(G1-9)**：5ステップ（業界13/職種11/役職7/関心19/読み口7）を `apps/mockup/src/data/profileOptions.ts` に実装。WP4.1登録フォームの前提クリア。
- ✅ **【環境・2026-06-04】gcloud CLI×Norton 恒久対処完了(G1-20)**：W1のADK/デプロイでgcloud CLI利用可能（対処方式は `GCP環境構築ログ.md` 参照）。
- ✅ **【デモ・2026-06-04】カット割り（秒単位・WP8.1旧案）を廃止→動画台本2本立てへ置換**：①プロダクト紹介2.5分(審査提出用)／②ピッチ内デモ60秒(体験オンリー)。台本アウトライン作成済（`publishr_other/demo/動画台本/`）。残＝録画(W5)。
- ✅ **【環境・2026-06-04】OAuth認証一式 完了**：同意画面を**Productionステータス**で設定（G1-19・refreshトークン長期有効化）・3スコープ・テストユーザー登録・OAuthクライアント`Publishr Web`発行・GitHub Secrets を **4本→6本**（GOOGLE_OAUTH_CLIENT_ID/_SECRET追加）。⚠️リダイレクトURIは仮`localhost:8080`のみ＝backendデプロイ後に本番URL追記（WBS 0.7）【GCP環境構築ログ.md】
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
- ✅ **【整合点検・2026-06-03】v2/IPO反映漏れを修正**：Firestoreルール favoriteAuthors を voiceStyle/format へ／`eval_set.json` を3層Profile＋8項目plan＋0-100・4観点で再構築／`.env.example` に予約上限・編集ラウンド・dev/prodガード追加／`calendar.json` に attendeesCount/recurring 補強／UI仕様書 本詳細をBookDraft 7フィールド・予約上限5冊に整合。**新規 `../design/langfuse-tracing.md` 作成**（G1-17）【点検：A群5件＋B群起票】
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
