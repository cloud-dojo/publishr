# Publishr 着手チェックリスト（v3・2026-06-05）

> 📑 全体の目次は [正本マップ](../README.md)／未決論点は [open-issues.md](open-issues.md)／ToDo・役割・スケジュールは [roles-and-ops.md](roles-and-ops.md)。
> **目的**: 「コードを書き始める前に潰すべきゲート」を1枚に固定する。設計・素材は揃った（§0）ので、本書は**握り・環境・残素材・着手前に決着すべき未決**に絞る。
> **着手順序**: 層1（友人MTGで握る）→ 層2（環境）→ 層3（鉄田の残素材）。層3は層1と並行可。
> **担当凡例**: 👥=2人で合意 / 🔧=友人（エンジニア）/ 📘=鉄田　｜　チェック: ☑=完了 / ☐=未 / ☐(任意)=任意

---

## 🧭 現在地（2026-06-05）

> **着手前ゲートの通過状況**：環境構築（層2）＋鉄田単独タスク（層3）に加え、**友人MTG（層1・2026-06-05）も完了＝着手前ゲートを全件クローズ**。W1（6/8〜）「ADK疎通」に進める。
> - ✅ 済：GCP基盤・IAM2人・OAuth一式(Production)・Secrets6本・リポ/collaborator・モノレポscaffold・prompts11本・Eval Set・サンプル3ソース
> - ✅ 済（鉄田単独・6/4）：initialProfile選択肢確定／gcloud×Norton恒久対処／デモ＝カット割り廃止→動画台本2本立てへ置換
> - ✅ MTG決着（6/5）：役割分担基本合意（基盤Firebaseのみ担当未定）・ADK実現性(一旦これでいく)・Drive Picker(G1-13=フォルダ単位)・Cloud Build方式(G1-18=方式A)・OAuth公開(G1-19=Production維持)・通知方式(G1-15=FCM不要)・**Firebase App Hosting の GitHub連携(G1-7)＝GitHub組織化→鉄田にオーナー権限→鉄田が連携実施（組織移管・鉄田オーナー権限は✅2026-06-05完了／連携作業はW1）**・連携/データ詳細(G1-3/5/6/7・I-19/I-9/I-20)を確定
> - 🟡 先送り：Langfuseトレース実装方式(G1-17＝OTel/SDK直は判断不可・今後検証)
> ※詳細な作業分解は [wbs.md](wbs.md)、論点の中身は [open-issues.md](open-issues.md)。

---

## §0. もう揃っているもの（作り直さない・着手の土台）

| 区分 | 状態 | 所在 |
|---|---|---|
| 要件・スコープ・DoD | ☑ | `../design/concept-summary.md`／`../design/mvp-scope.md` |
| 技術アーキ・データモデル・週次ロードマップ | ☑ | `../design/tech-architecture.md` |
| エージェントIPO（全7ステップ）・I/O契約・制御フロー | ☑ | `../design/agent-io-contract.md`／`adk-control-flow.md`／`agent-responsibilities.md` |
| **完成プロンプト＋良い/悪い出力例（全エージェント11本）** | ☑ | `../../packages/prompts/` |
| API契約・Firestoreルール・コスト概算・Langfuseトレース仕様 | ☑ | `../design/` 各MD |
| サンプル3ソース（Drive10/Calendar28/Tasks15・佐倉美咲） | ☑ | `../../packages/shared-schema/fixtures/{drive,calendar,tasks}.json` |
| Eval Set 8件（v2再構築・3層Profile/8項目plan/0-100/4観点） | ☑ | `../../eval/eval_set.yaml` |
| **GCP環境**（Project `publishr-498123`／Firestore/Storage/SA/Secret Manager/Firebase/予算アラート） | ☑ | `../infra/gcp-setup-log.md` |

---

## §1. 層1：友人MTG（全ての前提・これ無しで実装に進むと手戻り）

### 1-A. 合意ごと（👥）
| | 議題 | 完了条件 |
|---|---|---|
| ☑ | **①主要マイルストーン** | ✅合意（6/5）。W1=ADK疎通／W2=E2E縦通し を最重要として共有（撤退せず＝対策で乗り切る） |
| ☑ | **②役割分担の最終合意** | ✅基本合意（6/5）。友人＝エージェント実装＋基盤／鉄田＝フロント＋プロンプト設計＋Eval。境界＝`実行計画 §2`（設計=鉄田／実装=友人）。**※基盤Firebase部分のみ担当未定＝鉄田補助の可能性・後決め** |
| ☑ | **⑥タスク管理の置き場所** | ✅合意（6/5）。GitHub Projects / Notion / Todoist のいずれか1つに決め、W0〜W5（カテゴリA/B/C）を起票 |

### 1-B. 技術フィージビリティの握り（🔧）
| | 議題 | 出典 | 完了条件 |
|---|---|---|---|
| ☑ | **③ADK実現可能性** | G1-1 | ✅「一旦これでいく」で合意（6/5）。論点は残るがW1 Hello Worldで実証。NG時(6/14末)はSTEP2をLangGraphへ逃がす判断ラインも合意 |
| ☑ | **ADKでLoopAgent 2系統**が組めるか | 台帳ADK論点2 | ✅W1で実証する前提で合意。STEP2壁打ち＋編集ループ（STEP4 1R／モードB 最高3R）＝同一機構の使い回し |
| ☑ | **④3ソースAPI疎通** | G1-14 | ✅W1で疎通確認する段取りで合意（6/5）。Drive(drive.file)／Calendar(readonly)／Tasks(readonly) |
| ☑ | **⑤LLM-as-judge の CI組み込み** | MVP §9-5 | ✅方針合意。実装ルート=Gen AI Evaluation Service（GEAP）有力（I-21・C5.3） |

### 1-C. 着手前に決める設計判断（G系・🔧/👥）
| | 議題 | 台帳 | 決めること |
|---|---|---|---|
| ☑ | **Drive Picker連携** ★最重要 | G1-13 | ✅確定（6/5）＝Google Picker前提・**選択粒度＝フォルダ単位**でユーザー指定。`connectedSources.drive.folderIds[]` でサーバ保持。フロント=Picker UI(鉄田)／バック=ID保存・読取(一瀬) |
| 🟡 | **grounding課金** | G1-14 | 3ソース疎通はW1で確認の段取りで合意。**残＝調査サブB/CのGoogle検索groundingの課金有無・単価はW1疎通で確認**（Eval時はgrounding無効化等のガード） |
| ☑ | **通知方式** | G1-15 | ✅確定（6/5）＝MVP=アプリ内Firestore購読＋バナー（FCM不要） |
| 🟡 | **Langfuseトレース実装方式** | G1-17 | **先送り（6/5・判断不可）＝OTel経由 or Langfuse SDK直は今後W1以降に検証しながら確定**。3シグナル設計・仕様は`../design/langfuse-tracing.md`済 |
| ☑ | **連携方式・予約・トークン保存の確認** | G1-3/5/6/7 | ✅確定（6/5）＝Firestore直＋API3本／予約=POST /reserve（同時5冊チェック）／OAuth refresh=Secret Manager／CORS・ベースパス(`/api/*`集約・App Hosting本番+localhost:3000・GET/POST・Authorization/Content-Type) |
| ☑ | **観測ログ保存先・エラー方針** | I-19/I-20 | ✅確定（6/5）＝ObservationBundle保存先=`users/{uid}/observations/{YYYY-MM-DD}` サブコレクション／reserve=Firestore transaction・Pub/Sub冪等=status writing/publishedでスキップ・Jobは章分割保存で再開可 |
| ☑ | **Cloud Build↔GitHub接続方式** | G1-18 | ✅確定（6/5）＝**方式A（GitHub App直結）**。GitHub組織化→鉄田にオーナー権限付与で所有者依存が解消されるため、鉄田が GitHub App 直結で接続（旧推奨B=Actions主導は不採用）。現状トリガー未接続。実装はW4 |
| ☑ | **OAuth公開ステータスの最終確認** | G1-19 | ✅確定（6/5）＝**Production維持**（Testingだとrefreshトークン7日失効で週次自律バッチが停止）。OAuth実装担当=一瀬へ認識共有済 |
| ☑ | **Firebase App Hosting の GitHub連携**（フロント本番ホスティング） | G1-7 | ✅確定（6/5）＝フロント＝`apps/web` を App Hosting で公開。**組織移管（`cloud-dojo/publishr`）・鉄田オーナー権限は✅2026-06-05完了→鉄田が GitHub App 連携を実施**。設定値: live=`main`／root=`apps/web`／region=`asia-east1`／環境変数は `apps/web/apphosting.yaml` 済。鉄田準備(`apps/web/apphosting.yaml`・mockビルド)は**main マージ済み**(commit `29d5d3e`／旧PR #2=new-concept-v2統合で取込済)。残＝**鉄田が backend 作成＋GitHub App 連携→自動デプロイ→URL確認（W1）** |
| ☐ | **フロント本接続の前提一式**（鉄田が一瀬から受領・C4.9） | G1-3/7 | フロント(`apps/web`)は **mock で実装済**（Auth/Firestoreプロバイダ含む・休眠中）。本接続(mock→firestore)に一瀬から次を受領: ①**Firebase Web設定値**(`NEXT_PUBLIC_FIREBASE_*`) ②**Firestoreセキュリティルールのデプロイ** ③**API3本**(reserve/OAuth/trigger)の**URL・CORS** ④**Firestore docが`@publishr/shared-schema`形で保存・`ownerUid`規約**。これらが揃えば `NEXT_PUBLIC_DATA_SOURCE=firestore` で本接続。※デプロイ前は鉄田が**ローカルUI仕上げ(C4.8・行ずれ等の修正)**を先行 |

---

## §2. 層2：環境構築（MTG合意の直後）

### 2-1. GCP（大半 ☑済・残のみ）
| | タスク | 担当 | 状態 |
|---|---|---|---|
| ☑ | GCPプロジェクト・Firestore・Storage・SA・Secret Manager・Firebase・予算アラート | 🔧 | ✅ `publishr-498123` 構築済 |
| ☑ | **IAMで2人を招待**（鉄田のメール確定後） | 🔧 | ✅**2026-06-04完了**（ichisehiroshi@gmail.com 招待・権限付与済） |
| ☑ | **OAuth同意画面**（drive.file/calendar.readonly/tasks.readonly） | 🔧 | ✅**2026-06-04完了**。**Productionステータス**で設定（Testingだとrefreshトークン7日失効→自律バッチ停止を回避・G1-19）。テストユーザー登録済 |
| ☑ | **OAuthクライアント発行＋GitHub Secrets 6本**（CLIENT_ID/SECRET追加で4本→6本） | 🔧/📘 | ✅**2026-06-04完了**。クライアント`Publishr Web`発行・`GOOGLE_OAUTH_CLIENT_ID`/`_SECRET`登録済。⚠️リダイレクトURIは仮`localhost:8080`のみ→**本番URLはbackendデプロイ後に追記**（WBS B1.2） |

### 2-2. GitHub / モノレポ
| | タスク | 担当 | 完了条件 |
|---|---|---|---|
| ☑ | リポジトリ作成（private）・2人をcollaborator | 🔧 | ✅完了。**2026-06-05：個人リポ(`hiroshiichise/publishr`)から組織アカウント `cloud-dojo` へ移管完了→現 `cloud-dojo/publishr`・鉄田もオーナー権限付与済**。提出時public化は将来 |
| ☑ | **モノレポscaffold**：`apps/web` `apps/api` `agents` `packages/prompts` `packages/shared-schema` `eval` `infra` `docs` | 🔧 | ✅scaffold済（`agents/``apps/``packages/``eval/``docs/`存在。`infra/`はTerraform未投入＝W4） |
| ☑ | **共有スキーマの正本の置き場所**（Pydantic/TS/JSON Schemaのどれか）を `packages/shared-schema` で確定 | 👥 | ✅確定（6/5）＝`packages/shared-schema`（`@publishr/shared-schema`）に置く方針・改善方針を握った。型ドリフト防止（G1-11/B7）。**スキーマ内容の更新は鉄田が引き継ぎ** |
| ☑ | `packages/prompts` を投入（作成済11本を移植） | 📘 | ✅完了（`packages/prompts/`にMD投入済。旧`planning.json`はローダMD切替後に削除予定） |
| ☐ | ブランチ運用ルール（main保護＋feature＋軽量PR） | 👥 | 過剰にしない |
| ☐ | シークレット管理方針（`.env.example`はコミット／実値はSecret Manager／鍵はGit禁止） | 👥 | `.env.example`は更新済（予約上限・編集R・dev/prodガード） |

### 2-3. ローカル / CI空疎通
| | タスク | 担当 | 完了条件 |
|---|---|---|---|
| ☐ | ローカル環境統一（Python 3.11 / ADK SDK / Node） | 👥 | バージョン固定 |
| ☑ | **gcloud CLI×Norton の恒久対処** | 📘 | ✅**2026-06-04完了**。W1のADK/デプロイでgcloud CLI利用可能（対処方式の詳細は `../infra/gcp-setup-log.md` に追記）。 |
| ☐ | **CI/CD空パイプライン疎通**（push→Actions→Cloud Run "Hello"） | 🔧 | W1 Hello Worldと兼用 |

---

## §3. 層3：鉄田の残素材（層1と並行で今すぐ着手可）

| | タスク | 担当 | 完了条件 |
|---|---|---|---|
| ☑ | サンプル3ソース・Eval Set 8件（佐倉美咲） | 📘 | ✅完了（fixtures済・v2再構築済） |
| ☑ | 全エージェントの完成プロンプト＋良い/悪い出力例 | 📘 | ✅完了（`packages/prompts/`） |
| ☑ | **initialProfile 選択肢リストの確定**（業界/職種/役職/関心10〜20） | 📘 | ✅**2026-06-04完了**。5ステップ（業界13/職種11/役職7/関心19/読み口7）を `apps/web/src/data/profileOptions.ts`（正本）に実装（`apps/mockup/...` は参照コピー）。叩き台`API契約 §2-a`準拠 |
| ☑ | **デモ動画台本**（旧：カット割り秒単位） | 📘 | ✅**2026-06-04**＝カット割り廃止→**動画2本立て**に置換（①プロダクト紹介2.5分=審査提出用／②ピッチ内デモ60秒=体験のみ）。台本アウトライン作成済（`publishr_other/demo/動画台本/`）。残＝録画(W5) |
| ☐(任意) | personas.json（新フレーム voiceStyle/format）の数件サンプル | 📘 | 都度生成へ移行済のため任意。`著者ペルソナ集.md`は参照素材で足りる |
| ☐ | W1で各プロンプトを1回叩いてテスト→良い/悪い例を `eval/` fixtureへ兼用反映 | 📘+🔧 | スキーマ準拠・悪い例をreject確認（Langfuse実測） |

---

## §4. W1〜W5 関門チェック（週次・更新版）

> 各週の★関門を通過できなければ次週へ持ち越さず即対処。**W2が全体の山場**。

| 週 | 期間 | 一瀬の★関門 | 鉄田の★関門 |
|---|---|---|---|
| **W1** | 6/8-6/14 | ADKで「担当者立案→リーダーがスコア差し戻し（調査サブ=Google検索grounding）」が動く＋コスト/タイムアウト実測 | UIテンプレ選定・プロンプト実テスト（initialProfile確定✅／デモ動画台本✅は6/4完了） |
| **W2** ⚡ | 6/15-6/21 | STEP0(Drive＋Calendar＋Tasks)→STEP1(3層Profile)→STEP2(3階層)→Firestore保存（モードA骨格） | 書店トップ＋本詳細(BookDraft 7項目)をFirestore購読で表示・登録UI |
| **W3** | 6/22-6/28 | Scheduler曜日別起動＋STEP3キャスティング＋STEP4編集ループ(1R)＋予約→Pub/Sub→モードB本文編集ループ(最高3R) | 入荷理由F3・予約UI(同時5冊ガード)・読書/ハイライト・お気に入り著者UI・通知バナー |
| **W4** | 6/29-7/5 | GitHub Actions自動デプロイ・Langfuse計装(2ループ＋grounding)・Eval 8件ゲート・Terraform・firestore.indexes | FB UI・棚の充実・世界観・Eval観点最終調整 |
| **W5** | 7/6-7/12 | E2E通し・バグ潰し・dev/prodフラグをprodへ | デモ録画・ピッチ図解・README仕上げ |

---

## §5. 今すぐ動く「最初の3手」
1. ✅ 📘 ~~initialProfile選択肢の確定 ＋ デモ台本~~・gcloud×Norton恒久対処（**2026-06-04 すべて完了**／デモはカット割り廃止→動画台本2本立てへ置換）。
2. ✅ 📘 ~~友人MTG（6/5）で§1の全議題を握る~~（**2026-06-05 完了**＝役割分担基本合意・ADK一旦これでいく・Drive Pickerフォルダ単位・Cloud Build方式A・OAuth Production維持・連携/データ詳細を確定。Langfuse実装方式のみ先送り）。
3. 📘🔧 **次の一手：GitHub組織化→鉄田にオーナー権限付与→鉄田が App Hosting/Cloud Build 連携／CI空パイプ疎通**（リポ/scaffold/GCPは構築済）→ W1 ADK疎通へ。鉄田は C4.8 UIローカル仕上げ・共有スキーマ正本確定(A5.2)を先行。
