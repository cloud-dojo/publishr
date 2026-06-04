# Publishr WBS（Work Breakdown Structure・2026-06-03）

> 📑 関連: [正本マップ](../README.md)／[kickoff-checklist.md](kickoff-checklist.md)（着手ゲート）／[roles-and-ops.md](roles-and-ops.md)（週次・役割）／[open-issues.md](open-issues.md)（未決論点）。
> **目的**: MVPを「動くデモ動画＋再現可能リポジトリ」まで到達させる作業を、成果物単位のワークパッケージ(WP)に分解し、担当・依存・週・完了条件(DoD)を付ける。
> **前提**: 実働約5週間（W1〜W6・実質W2〜W5）／体制＝友人1.0＋鉄田0.5〜1.0／設計・プロンプト・Eval素材・GCP環境は✅済（チェックリスト §0）。
> **担当**: 🔧友人（エージェント・基盤・DevOps）／📘鉄田（フロント・プロンプト・Eval設計・デモ）／👥両者。
> **見積り粒度**: 週単位（W）。人日は出さない（少人数のため週マッピングで管理）。
> **クリティカルパス**: WP0 → WP1.1(ADK疎通) → **WP1.2-1.4＋WP4.2-4.3 のE2E縦通し（W2★最重要）** → WP2/WP6 → WP8（録画）。

---

## 🧭 現在地サマリ（2026-06-04時点）

> **いまどこ**: **着手前の準備フェーズ（実装は未開始）**。設計・プロンプト・Eval・GCP基盤・OAuth認証まで整い、**コードを書き始める一歩手前**（友人MTGの握り待ち）。次の山場は W1「ADK疎通」→ W2「E2E縦通し」。
>
> **✅ できている（土台）**
> - 設計docs一式／完成プロンプト11本（`packages/prompts/`）／Eval Set 8件（`eval/eval_set.yaml`）
> - GCP基盤（`publishr-498123`：Firestore/Storage/SA/Secret Manager/Firebase/予算アラート）
> - **【6/4完了】GCP IAM 2人招待・OAuth同意画面(Production)・テストユーザー・OAuthクライアント`Publishr Web`発行・GitHub Secrets 計6本**（GCP_PROJECT_ID／GCP_SA_KEY／GOOGLE_OAUTH_CLIENT_ID／SECRET／LANGFUSE×2）
> - GitHubリポ（一瀬所有・鉄田=collaborator）／モノレポscaffold（agents・apps・packages・eval・docs）／計画docsをrepoへ統合
>
> **【6/4完了・鉄田単独タスク】** initialProfile選択肢リスト(G1-9・WP5.2)✅／gcloud CLI×Norton 恒久対処(G1-20)✅／デモはカット割り廃止＝**動画台本2本立て**(2.5分=審査提出用／60秒=ピッチ内・WP8.1)へ置換✅
>
> **⏳ 着手前に残っているゲート**（＝これを潰さないとW1に進めない／手戻りする）
> - **友人MTG（最重要・唯一の残ゲート）**: ADK実現性(G1-1)・役割分担(G1-2)・**Drive Picker(G1-13)**・Cloud Build接続方式A/B(G1-18)・OAuth公開ステータス(G1-19)・通知方式(G1-15) を握る
> - **環境の積み残し**: OAuth本番リダイレクトURI追記（backendデプロイ後・WP0.7／現状は仮の`localhost`のみ）
> - **フロント本番ホスティング（WP0.8・G1-7）**: ホスティング=Firebase App Hosting／フロント=Next.js(`apps/web`)で確定。鉄田準備(apphosting.yaml・mockビルド・**PR #2**)✅。**🔴ブロック=App Hosting の GitHub App 連携はリポ所有者(一瀬)のみ可**→明日MTGで一瀬が backend 作成 or GitHub App 許可で解除
>
> ※状態マーク: **✅完了 ／ 🔜着手前（準備OK）／ ⏸MTG待ち**。各WP表のDoD列末尾に状態を付す。W1以降の実装WPは原則すべて 🔜/⏸（コード未着手）。

---

## WBS 全体ツリー
```
Publishr MVP
├─ WP0 準備・基盤（W0-W1・👥/🔧）
├─ WP1 自律企画エージェント（モードA／ADK）（W1-W3・🔧 ※プロンプトは📘）
├─ WP2 後追い執筆（モードB）（W3・🔧）
├─ WP3 データ/状態基盤（Firestore/GCS）（W2-W3・🔧）
├─ WP4 フロント（書店UI）（W2-W4・📘）
├─ WP5 プロンプト/中身の質（W1-W4・📘）
├─ WP6 DevOps / Observability（W4・🔧）
├─ WP7 Eval / 品質ゲート（W1-W4・📘+🔧）
├─ WP8 デモ・提出物（W4-W6・📘）
└─ WP9 コスト・運用・横断（全期間・👥）
```

---

## WP0. 準備・基盤（W0-W1）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 0.1 | 友人MTG（チェックリスト§1の全議題を握る） | 👥 | — | W0 | マイルストーン・役割・G系(Picker/grounding/通知/Langfuse方式)合意 ⏸**未開催（明日夕方予定）＝最優先** |
| 0.2 | GCP IAM 2人招待・OAuth同意画面（3スコープ・テストユーザー） | 🔧 | 0.1 | W0 | デモ垢で3ソース承認可（GCP本体は✅済） ✅**2026-06-04完了**（IAM 2人・同意画面Production・テストユーザー・クライアント`Publishr Web`発行・Secrets計6本） |
| 0.3 | GitHubリポ作成・モノレポscaffold（apps/web・apps/api・agents・packages/{prompts,shared-schema}・eval・infra・docs） | 🔧 | 0.1 | W0-1 | 2人がpush可・ディレクトリ確定 ✅**リポ作成・collaborator・scaffold済**（infra/Terraformは空＝W4で投入） |
| 0.4 | 共有スキーマの正本確定（Pydantic/TS/JSON Schema）＋packages/promptsを投入 | 👥/📘 | 0.3 | W1 | 型ドリフト防止の単一ソース（G1-11） 🔜prompts投入✅／スキーマ正本の置き場所はMTGで確定 |
| 0.5 | CI/CD空パイプライン疎通（push→Actions→Cloud Run "Hello"） | 🔧 | 0.3 | W1 | 自動デプロイの土台（W1 Hello Worldと兼用） 🔜着手前 |
| 0.6 | ローカル環境統一（Python3.11/ADK SDK/Node） | 👥 | 0.3 | W1 | バージョン固定 |
| 0.7 | **OAuth本番リダイレクトURI追記**（クライアント`Publishr Web`に `https://<backendのCloud Run URL>/api/auth/google/callback` を追加） | 🔧/📘 | backendデプロイ | W2-4 | 現状は仮 `http://localhost:8080/...` のみ。**バックエンドURL確定後**に本番URLを追記（CLIENT_ID/SECRETは不変）。OAuth一式・同意画面・スコープ・Secrets 2本は2026-06-04に✅済（GCP環境構築ログ参照） |
| 0.8 | **Firebase App Hosting backend 作成（フロント本番ホスティング・GitHub App連携）** | 🔧一瀬 | 0.1 | W1 | `apps/web` を App Hosting で mock 公開（Netlifyから移行・G1-7）。設定: live=`main`／root=`apps/web`／region=`asia-east1`／環境変数=`apps/web/apphosting.yaml`。**GitHub App連携はリポ所有者=一瀬のみ可**（鉄田collaborator不可）。鉄田準備(apphosting.yaml・mockビルド・**PR #2**)は✅。⏸**一瀬対応待ち**→解除後 PR #2 マージで自動デプロイ・URL確認・Netlify退役 |

## WP1. 自律企画エージェント（モードA・ADK）（W1-W3）
| ID | タスク | 担当 | 依存 | 週 | DoD（IO契約参照） |
|---|---|---|---|---|---|
| 1.1 | ★**ADK疎通(MiniLoop)**：担当者立案→リーダーがスコア差し戻し（調査サブ=grounding）／escalate・max_iterations実証 | 🔧 | 0.5 | **W1** | 再ループ・脱出が動く。NG時LangGraph判断（ADK §7） |
| 1.2 | STEP0 観測ツール（Drive/Calendar/Tasks ±14日・生データ・**Picker連携サーバ側**） | 🔧 | 0.2,1.1 | W2 | ObservationBundle生成（§2／G1-13） |
| 1.3 | STEP1 読者分析（Pro・**3層Profile**） | 🔧 | 1.2 | W2 | ReaderProfile{base/currentWork/readingBehavior}保存（§3） |
| 1.4 | STEP2 企画3階層（調査サブ×3→担当者→リーダー壁打ちLoop最高3R） | 🔧 | 1.1,1.3 | W2 | PlanProposal 8項目確定・score/rounds記録（§4） |
| 1.5 | STEP3 キャスティング（架空著者5人・voiceStyle×format 2軸） | 🔧 | 1.4 | W2-3 | GeneratedPersonaSet 5人（§5-3a） |
| 1.6 | STEP4 プレビュー編集ループ（編集長⇄著者・1R・3観点） | 🔧 | 1.5 | W3 | BookDraft 7項目×5冊 draft保存（§5-2） |
| 1.7 | STEP5 装丁（Imagen・dev時モック） | 🔧 | 1.6 | W3 | coverUrl付与（§6・ENABLE_IMAGEN） |
| 1.8 | Cloud Scheduler 曜日別トリガー（土/水/日） | 🔧 | 1.4 | W3 | 自律起動で棚更新（デモは手動起動可） |

## WP2. 後追い執筆（モードB）（W3）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 2.1 | 予約API `POST /reserve`（draft→reserved＋**同時5冊チェック**＋Pub/Sub発行） | 🔧 | 3.1 | W3 | API契約 §3・I-16 |
| 2.2 | Pub/Sub → 執筆ワーカー起動 | 🔧 | 2.1 | W3 | 冪等ガード（I-20） |
| 2.3 | 本文編集ループ（編集長⇄著者・最高3R・弱い章のみ改稿・約100p） | 🔧 | 1.6,2.2 | W3 | published・editRounds記録（§7） |

## WP3. データ/状態基盤（Firestore/GCS）（W2-W3）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 3.1 | Firestoreスキーマ＋セキュリティルール（ownerUid・直書き許可フィールド・3層profile・favoriteAuthors voiceStyle/format） | 🔧 | 0.2 | W2 | ルール本文デプロイ（FIRESTORE） |
| 3.2 | **複合インデックス列挙＋firestore.indexes.json**（棚/書庫クエリ） | 🔧 | 4.2,4.7 | W2-3 | 実行時エラー回避（I-15） |
| 3.3 | GCS本文保護（署名付きURL or IAM） | 🔧 | 2.3 | W3 | 他者本文を読めない（I-10） |
| 3.4 | 観測ログ保存先コレクション（observationLogs等） | 🔧 | 1.2 | W2 | STEP0直書き可（I-19） |

## WP4. フロント（書店UI）（W2-W4・📘）
| ID | タスク | 担当 | 依存 | 週 | DoD（UI仕様書参照） |
|---|---|---|---|---|---|
| 4.1 | 登録フォーム＋OAuth接続＋**Drive Pickerファイル選択UI** | 📘 | 0.4,1.2 | W2 | initialProfile直書き・3ソース接続（3-2/3-3・G1-13） |
| 4.2 | 書店トップ（入荷一覧・F3入荷理由） | 📘 | 3.1 | W2 | draft本＋入荷理由表示（3-4） |
| 4.3 | 本詳細（**BookDraft 7項目**・books由来） | 📘 | 3.1,1.6 | W2-3 | title/subtitle/今あなたは/解決する課題/核心/アジェンダ/序文（3-6） |
| 4.4 | 著者選択・予約UI（**同時5冊ガード**） | 📘 | 2.1 | W3 | reserve呼び出し・上限表示（3-7） |
| 4.5 | 読書画面・ハイライト・簡易FB（Firestore直書き） | 📘 | 3.1 | W3 | ハイライト保存・FB記録（3-9/3-10） |
| 4.6 | お気に入り著者保存（favoriteAuthors・name/voiceStyle/format） | 📘 | 3.1 | W3 | arrayUnion保存（3-11） |
| 4.7 | わたしの書庫・通知バナー（Firestore購読） | 📘 | 4.2 | W4 | 入荷/執筆完了の購読バナー（3-5・G1-15） |

## WP5. プロンプト/中身の質（W1-W4・📘）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 5.1 | 完成プロンプト＋良い/悪い例（11本） | 📘 | — | — | ✅完了（packages/prompts） |
| 5.2 | initialProfile 選択肢リスト確定 | 📘 | — | W1 | 業界/職種/役職/関心10〜20（G1-9） ✅**2026-06-04完了**（5ステップ：業界13/職種11/役職7/関心19/読み口7。`apps/mockup/src/data/profileOptions.ts`） |
| 5.3 | W1 各プロンプト実テスト→調整（スキーマ準拠・悪い例reject） | 📘+🔧 | 1.1 | W1-2 | Langfuseで出力確認 |
| 5.4 | 良い/悪い例を eval fixture に兼用反映 | 📘 | 5.3,7.1 | W2 | few-shot＋Eval両用 |

## WP6. DevOps / Observability（W4・🔧）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 6.1 | GitHub Actions → Cloud Build → Cloud Run 自動デプロイ | 🔧 | 0.5 | W4 | mainマージで自動デプロイ |
| 6.2 | **Eval judgeゲート**（8件・本命<70で停止・87.5%通過）をCIに組込 | 🔧 | 7.x | W4 | failでデプロイ停止（MVP §9） |
| 6.3 | Langfuse計装（**2ループ＋grounding取得URL**） | 🔧 | 1.4,1.6,2.3 | W4 | 必然性の証跡が可視化（Langfuseトレース仕様） |
| 6.4 | Terraform IaC（Cloud Run/Scheduler/Pub-Sub/IAM/indexes） | 🔧 | 各基盤 | W4 | コア資源をコード化 |

## WP7. Eval / 品質ゲート（W1-W4・📘+🔧）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 7.1 | Eval Set 8件（v2・3層/8項目/0-100/4観点） | 📘 | — | — | ✅完了（eval_set.json） |
| 7.2 | judge再現性テスト（同一対象を複数回採点・標準偏差確認） | 📘+🔧 | 5.3 | W2-3 | ゲート判定の信頼度確認 |
| 7.3 | 閾値・ルーブリックの運用調整（企画70・プレビュー緩め・本文5観点） | 📘 | 7.2 | W4 | 実データで微調整（I-1/I-18） |

## WP8. デモ・提出物（W4-W6・📘）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 8.1 | デモ動画台本（必然性3証跡を画に） | 📘 | — | W1-4 | ~~カット割り（秒単位）~~→**動画2本立てに置換**：①プロダクト紹介2.5分(審査提出用・必然性を動画内で見せる)／②ピッチ内デモ60秒(体験オンリー)。台本アウトライン✅**2026-06-04**（`publishr_other/demo/動画台本/`）。残＝録画 |
| 8.2 | デモのデータ戦略（seed投入 or ライブ／dev-prod切替） | 👥 | 全機能 | W5 | 録画再現性確保（I-14） |
| 8.3 | デモ録画（カット編集で予約→入荷） | 📘 | 8.1,8.2 | W5 | 提出動画 |
| 8.4 | ピッチ図解（自律アーキ・必然性・ループB将来） | 📘 | — | W4-5 | スライド |
| 8.5 | README仕上げ（再現可能性） | 📘 | 全体 | W5 | 起動手順・構成図 |
| 8.6 | リポジトリpublic化・最終提出 | 👥 | 8.3,8.5 | W6 | 7/10締切 |

## WP9. コスト・運用・横断（全期間・👥）
| ID | タスク | 担当 | 依存 | 週 | DoD |
|---|---|---|---|---|---|
| 9.1 | dev/prodフラグ運用（本文ページ/Imagen/冊数・.env） | 👥 | 0.6 | W1- | dev既定で反復、本番のみprod |
| 9.2 | コスト実測→コスト概算.md上書き（Proベース実単価） | 🔧→📘 | 1.1 | W1 | 予算¥10,000耐性確認 |
| 9.3 | エラー/リトライ/冪等/タイムアウト方針 | 🔧 | 1.x,2.x | W1-3 | 最小方針を決め実装（I-20） |

---

## 週次マッピング（WBS×週）
| WP | W1 | W2⚡ | W3 | W4 | W5 | W6 |
|---|---|---|---|---|---|---|
| WP0 基盤 | ●● | | | | | |
| WP1 モードA | 1.1★ | 1.2-1.4 | 1.5-1.8 | | | |
| WP2 モードB | | | 2.1-2.3 | | | |
| WP3 データ基盤 | | 3.1/3.4 | 3.2/3.3 | | | |
| WP4 フロント | | 4.1-4.3 | 4.4-4.6 | 4.7 | | |
| WP5 プロンプト | 5.2/5.3 | 5.4 | | | | |
| WP6 DevOps | | | | 6.1-6.4 | | |
| WP7 Eval | 7.1✅ | 7.2 | 7.2 | 7.3 | | |
| WP8 デモ | 8.1 | | | 8.4 | 8.2/8.3/8.5 | 8.6 |
| WP9 横断 | 9.1/9.2 | | 9.3 | | | バッファ |

## マイルストーン
| MS | 週 | 判定 |
|---|---|---|
| M1 ADK疎通 | W1末 | 1.1★が動く（最大リスク解消） |
| **M2 E2E縦通し** | **W2末** | **Drive観測→企画→棚に並ぶ（1.2-1.4＋4.2-4.3）＝全体の山場** |
| M3 自律＋執筆 | W3末 | Scheduler起動＋予約→本文編集ループで読める（1.8/2.x/4.4-4.6） |
| M4 DevOps/L4 | W4末 | CIにEvalゲート＋Langfuse 2ループ可視化（6.x） |
| M5 提出物完成 | W5末 | 録画＋README（8.3/8.5） |
| M6 提出 | W6 | public化・提出（8.6） |

> **遅延時の原則**: W2のM2を死守（横に作り込まず縦に細く通す）。詰まればSTEP2のみLangGraphへ（ADK §8）。Stretch（粒度選択/ES/ループB実装）はW6余力次第。
