# Publishr 着手チェックリスト（v3・2026-06-05）

> 📑 全体の目次は [正本マップ](../README.md)／未決論点は [open-issues.md](open-issues.md)／ToDo・役割・スケジュールは [roles-and-ops.md](roles-and-ops.md)。
> **目的**: 「コードを書き始める前に潰すべきゲート」を1枚に固定する。設計・素材は揃った（§0）ので、本書は**握り・環境・残素材・着手前に決着すべき未決**に絞る。
> **着手順序**: 層1（友人MTGで握る）→ 層2（環境）→ 層3（鉄田の残素材）。層3は層1と並行可。
> **担当凡例**: 👥=2人で合意 / 🔧=友人（エンジニア）/ 📘=鉄田　｜　チェック: ☑=完了 / ☐=未 / ☐(任意)=任意

---

## 🧭 現在地（2026-06-04）

> **着手前ゲートの通過状況**：環境構築（層2）＋鉄田単独タスク（層3）は**✅完了**。**残るゲートは ①友人MTGの握り（層1・本日6/5夕方予定）のみ**。これを通過すれば W1（6/8〜）「ADK疎通」に進める。
> - ✅ 済：GCP基盤・IAM2人・OAuth一式(Production)・Secrets6本・リポ/collaborator・モノレポscaffold・prompts11本・Eval Set・サンプル3ソース
> - ✅ 済（鉄田単独・6/4）：initialProfile選択肢確定／gcloud×Norton恒久対処／デモ＝カット割り廃止→動画台本2本立てへ置換
> - ⏸ MTG待ち：役割分担最終合意・ADK実現性・Drive Picker(G1-13)・Cloud Build方式(G1-18)・OAuth公開(G1-19)・通知方式(G1-15)・**Firebase App Hosting の GitHub連携(G1-7・🔧一瀬／鉄田準備✅・PR #2)**
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
| ☐ | **①主要マイルストーン** | W1=ADK疎通／W2=E2E縦通し を最重要として共有（撤退せず＝対策で乗り切る） |
| ☐ | **②役割分担の最終合意** | 友人＝エージェント実装＋基盤／鉄田＝フロント＋プロンプト設計＋Eval。境界＝`実行計画 §2`（設計=鉄田／実装=友人） |
| ☐ | **⑥タスク管理の置き場所** | GitHub Projects / Notion / Todoist のいずれか1つに決め、W0〜W5（カテゴリA/B/C）を起票 |

### 1-B. 技術フィージビリティの握り（🔧）
| | 議題 | 出典 | 完了条件 |
|---|---|---|---|
| ☐ | **③ADK実現可能性** | G1-1 | 「担当者が立案→リーダーがスコアで差し戻し」がW1で動く感触。NG時はSTEP2をLangGraphへ逃がす判断 |
| ☐ | **ADKでLoopAgent 2系統**が組めるか | 台帳ADK論点2 | STEP2壁打ち＋編集ループ（STEP4 1R／モードB 最高3R）＝同一機構の使い回し |
| ☐ | **④3ソースAPI疎通** | — | Drive(drive.file)／Calendar(readonly)／Tasks(readonly) が個人アカウントで叩けるか |
| ☐ | **⑤LLM-as-judge の CI組み込み** | MVP §9-5 | GitHub ActionsでGeminiスコア取得→Eval判定が5週で可能か |

### 1-C. 着手前に決める設計判断（G系・🔧/👥）
| | 議題 | 台帳 | 決めること |
|---|---|---|---|
| ☐ | **Drive Picker連携** ★最重要 | G1-13 | drive.fileはDrive走査不可→Google Picker前提を確定。選択粒度（ファイル/フォルダ）・folderIds/fileIdsの取得とサーバ保存・鉄田/友人の責務線 |
| ☐ | **grounding課金** | G1-14 | 調査サブB/CのGoogle検索groundingの課金有無・単価。Eval多回実行時のガード（Eval時はgrounding無効化等） |
| ☐ | **通知方式** | G1-15 | MVP=アプリ内Firestore購読＋バナーで確定（FCM不要）の合意 |
| ☐ | **Langfuseトレース実装方式** | G1-17 | OTel経由 or Langfuse SDK直／grounding取得URLの取得元。仕様は`../design/langfuse-tracing.md`済 |
| ☐ | **連携方式・予約・トークン保存の確認** | G1-3/5/6/7 | Firestore直＋API3本／予約=POST /reserve（同時5冊チェック）／OAuth refresh=Secret Manager／CORS・ベースパス |
| ☐ | **観測ログ保存先・エラー方針** | I-19/I-20 | ObservationBundleの保存先コレクション／Pub/Sub冪等キー・reserveトランザクション・Jobタイムアウトの最小方針 |
| ☐ | **Cloud Build↔GitHub接続方式 A/B** | G1-18 | 論点＝自動デプロイの繋ぎ方。**A=GitHub App接続（個人リポなので所有者=一瀬のみ可）／B=Actionsから`gcloud builds submit`（鉄田側で完結・推奨）**。現状トリガー未接続を確認済。**AかBを握るだけ**（実装はW4） |
| ☐ | **OAuth公開ステータスの最終確認** | G1-19 | 論点＝Testingだとrefreshトークン7日失効で週次自律バッチが停止。**現状Production設定済→「Production維持」で握る**。OAuth実装担当=一瀬につき確認 |
| ☐ | **Firebase App Hosting の GitHub連携**（フロント本番ホスティング・🔧一瀬） | G1-7 | フロント＝`apps/web` を App Hosting で公開（決定済）。**GitHub App 連携はリポ所有者=一瀬のみ可**（鉄田collaborator不可で着手ブロック）→ **一瀬が backend 作成 or GitHub App 許可**。設定値: live=`main`／root=`apps/web`／region=`asia-east1`／環境変数は `apps/web/apphosting.yaml` 済。鉄田準備(apphosting.yaml・mockビルド・PR #2)は✅。解除後は PR #2 マージ→自動デプロイ→URL確認 |
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
| ☑ | リポジトリ作成（private）・2人をcollaborator | 🔧 | ✅完了（`hiroshiichise/publishr`・鉄田collaborator・招待受領済）。提出時public化は将来 |
| ☑ | **モノレポscaffold**：`apps/web` `apps/api` `agents` `packages/prompts` `packages/shared-schema` `eval` `infra` `docs` | 🔧 | ✅scaffold済（`agents/``apps/``packages/``eval/``docs/`存在。`infra/`はTerraform未投入＝W4） |
| ☐ | **共有スキーマの正本の置き場所**（Pydantic/TS/JSON Schemaのどれか）を `packages/shared-schema` で確定 | 👥 | 型ドリフト防止（G1-11/B7）。**MTGで握る** |
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
| ☑ | **initialProfile 選択肢リストの確定**（業界/職種/役職/関心10〜20） | 📘 | ✅**2026-06-04完了**。5ステップ（業界13/職種11/役職7/関心19/読み口7）を `apps/mockup/src/data/profileOptions.ts` に実装。叩き台`API契約 §2-a`準拠 |
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
2. 📘 **友人MTG（本日6/5夕方）で§1の全議題を握る**＝特にG1-13 Picker・G1-17 Langfuse方式・役割分担。**鉄田単独タスクは完了済→残ゲートはこのMTGのみ**。
3. 🔧 **MTG後：CI空パイプ疎通**（リポ/scaffold/GCPは構築済）→ W1 ADK疎通へ。
