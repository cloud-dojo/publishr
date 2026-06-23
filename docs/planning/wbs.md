# Publishr WBS（Work Breakdown Structure・実装正本・2026-06-07）

> 📑 関連: [正本マップ](../README.md)／[kickoff-checklist.md](kickoff-checklist.md)（着手ゲート）／[roles-and-ops.md](roles-and-ops.md)（週次・役割）／[open-issues.md](open-issues.md)（未決論点）。
> **本書の位置づけ（単一正本）**: **作業分解（A/B/C）＋実装順序（WBS IDの直列）＋ゲート＋検証**を1枚に統合した**エージェント実施の正本**。Claude Code / Cursor エージェントは**本書を読み込んで実施**する。MVPローカルスコープの骨格は [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)（ローカル一まわり）を補助参照。
> **ゴール**: **7/10提出・動くデモ動画＋再現可能リポジトリ・機能凍結6/30**。実装順序もタスクIDも**すべて WBS（A/B/C0/C1…）で一本化**する（旧 Phase P0a〜P7 表記は廃止）。
> **構造の方針**: **カテゴリを主役（レベル1）**にし、**時間（週）は各表の1列（属性）に格下げ**。着手順は冒頭「§エージェント実施ガイド」の**WBS直列**が正。時間軸での見え方は末尾「時間軸ビュー（参考）」に温存。
> **前提**: 実働約5週間（W1〜W5）／体制＝一瀬1.0＋鉄田0.5〜1.0／設計・プロンプト・Eval素材・GCP環境は✅済（チェックリスト §0）。
> **クリティカルパス**: B(基盤) → ~~C1.0(ADK疎通)~~（✅） → **C1.1-C1.3＋C4のE2E縦通し（W2★最重要）** → C2/C5 → C6（録画）。

> **🧑‍🤝‍🧑 担当の凡例（3パターン）**: **鉄田**（=あなた・フロント/プロンプト/Eval設計/デモ担当）／**一瀬**（=友人エンジニア・エージェント/基盤/DevOps担当）／**鉄田・一瀬**（2人で一緒にやる）。割り当ては [roles-and-ops.md](roles-and-ops.md) の役割分担表に準拠。
> **🔑 権限オーナーの前提（MTG 2026-06-05で更新）**: **Google Cloud のオーナー権限＝鉄田**／**GitHub＝組織アカウント `cloud-dojo` を新規作成し現リポを `cloud-dojo/publishr` へ移管→鉄田にもオーナー権限を付与（✅2026-06-05完了）**。これにより**App Hosting の GitHub App 連携(B3.3)・Cloud Build↔GitHub 接続(方式A・G1-18)は鉄田が実施**できる（旧「GitHub系＝一瀬のみ」の所有者依存は解消）。コードを書く実装タスクは役割分担表どおり。※基盤Firebase部分（Firestore/GCS）の担当は未定＝鉄田が一瀬を補助する可能性あり（後決め）。
> **📅 予定週の凡例（実日付・今日=6/7基準）**: 週は月曜はじまり。**W0=6/1–6/7**（準備・本日締め）／**W1=今週=6/8–6/14**／**W2=6/15–6/21**（★E2E山場）／**W3=6/22–6/28**／**W4=6/29–7/5**／**W5=7/6–7/12**（7/10提出）。各表の「予定週」列に `W2（6/15–21）` の形で明記。
> **状態マーク**: ✅完了 ／ 🔜着手前（準備OK）／ ⏸MTG・他者待ち ／ 🟡進行中/mock実装済 ／ 🔴ブロック。

---

# エージェント実施ガイド（実装順序・ゲート・検証）

> **エージェントへの指示**: **①下の「実装順序」で今どの WBS ID か確認 → ②該当セクションの表を読む → ③ゲートを満たしてから次へ**。横の作り込みより縦串（観測→企画→棚→予約→執筆→読める）を優先。

## 実装順序（WBS ID・上から順に着手）

| 順 | WBS ID | ゲート | 目的（1行） | 主担当 | クラウド/課金 |
|---|---|---|---|---|---|
| 1 | **C0.1** | C0.1 | mock回帰復旧 | 鉄田 | なし |
| 2 | **C0.2** | C0.2 | 実装シーム敷設（mock挙動不変） | 鉄田 | なし |
| 3 | **B1.3** | — | GCP基盤 確認/構築＋ADC | 鉄田 | 基盤のみ・微小 |
| 4 | **C1.0.1** | **C1.0.1★** | ADK MiniLoop 実escalate実証 | **一瀬** | LLM少 |
| 5 | **C1.1–C1.6**＋**C3.x**＋B3.1 | — | モードA全STEP＋Firestore＋最小運用足場 | **一瀬** | LLM中 |
| 6 | **C4.8/C4.9**＋C1観測本接続 | **M2★** | E2E縦通し（ブラウザ）＋最小Cloud Run | 鉄田・一瀬 | LLM中 |
| 7 | **C2.x**＋**C1.7** | M3 | モードB執筆（段階）＋Scheduler自律 | **一瀬** | LLM大 |
| 8 | **C5.3/5.6**＋**B3.2**＋**B4.1** | M4 | Evalゲート(GEAP)＋CI/CD＋IaC完成 | 一瀬・鉄田 | LLM中 |
| 9 | **C6.x** | M5/M6 | デモ・提出物→7/10 | 鉄田・一瀬 | — |

**直列の幹**: C0.1→C0.2→B1.3→C1.0.1→(C1.1–C1.6+C3)→(C4+E2E)→(C2+C1.7)→(C5+B3+B4)→C6。**並行可**: C4.8・C5.1・C6.1/6.7（鉄田）は C1.0.1/C1.1以降と並行。

## 設計原則（全タスク共通・不変条件）

1. **mock経路＝常時回帰の床**。`PUBLISHR_LLM=mock`／`DATA_SOURCE=mock`／`NEXT_PUBLIC_DATA_SOURCE=mock` でクラウド・課金ゼロ。`make verify`＋`make eval`＋`make pipeline`＋`make smoke` を常に緑。
2. **縦に細く通す（W2 E2E死守）**。横の作り込みより「観測→企画→棚→予約→執筆→読める」の縦串を最優先。
3. **最大リスク先行**: 実LLM escalate（**C1.0.1**）は **2026-06-06 通過済み**。次は W2 E2E（C1.1–C1.3＋C4）を死守。詰まれば STEP2（**C1.3**）のみ LangGraph へ（[adk-control-flow.md](../design/adk-control-flow.md) §8）。
4. **撤退ライン**: ~~W1=C1.0.1~~（達成）／**W2=E2E(C4+C1.1–C1.3)**。通らなければ PatentSentinel へ退避（事前合意）。
5. **運用リスク前倒し**: 最小 Cloud Run・最小 CI・Firestore rules 検証は C3/C4 で入れる。C5/B3/B4 の完成形は後半。
6. **コード規律**: small-files（200–400行・最大800）、immutability、入力検証、秘密は Secret Manager/env。
7. **コスト暴走はコード側で止める**: Budget通知は保険。主防御＝mock既定・dev実行縮小・`max_iterations`/冊数/ページ数/Imagen/timeout/推定cost上限・公開APIの認証/許可uid/連打防止。

## ゲート（未達なら次の WBS ブロックへ進まない）

| ゲート | 条件 | ブロックする先 | 状態 |
|---|---|---|---|
| **C0.1** | `make verify`＋`make eval`＋`make pipeline`＋`make smoke` 全緑。`eval_set.yaml`↔`eval_harness.py` 整合 | C0.2以降すべて | ✅**2026-06-06 完了** |
| **C0.2** | v2 I/O・prompt loader・`PUBLISHR_LLM` dispatcher・コストガード。mock挙動差分ゼロ＋loader単体テスト緑 | C1.0.1以降 | ✅**2026-06-06 完了** |
| **C1.0.1★** | MiniLoopが実Vertexで再実行可。score差し戻し→再提出→`escalate`脱出。Langfuse trace・成功JSON・`@pytest.mark.vertex` 最小テスト。devプロファイル固定 | C1.1–C1.6/C3 本格実装 | ✅**2026-06-06 完了**（H2実証・固定success JSONファイルのコミットは任意残） |
| **C4前** | Cloud Run外部公開＋`PUBLISHR_LLM=vertex`＋`DATA_SOURCE=firestore` の前に: Firebase IDトークン検証・Firestore rulesデプロイ（**C3.1**）・OAuth `state` 検証・手動トリガー許可uid・レート制限 | C4.9 本番接続 | 🔜着手前 |

## インフラ構築段階（WBSブロックごと）

| WBSブロック | できるインフラ | 粒度 | 次への意味 |
|---|---|---|---|
| C0 | なし（ローカルmock） | `.env` 全mock | 常時回帰の床 |
| B1.3 | GCP基盤の器 | Project/API/Firestore/GCS/SA/Secret/ADC確認 | C1.0.1でVertex呼べる |
| C1.0.1 | Vertex/Langfuse疎通（✅H2完了） | ローカルCLIのみ。Cloud Run等は作らない | ADKランタイムリスク切り出し済み→C1.1へ |
| C1+C3 | Firestore実データ層＋最小CI足場 | `DATA_SOURCE=firestore`・rules/index・Dockerfile雛形 | 実DBに棚データ |
| C4 | API最小Cloud Run | `/health`・planning trigger・手動確認 | ローカル外でも縦串 |
| C2+C1.7 | 本番寄り実行基盤 | API/worker/planning Job・Pub/Sub・Scheduler・App Hosting | 予約→執筆→自律棚更新 |
| C5+B3+B4 | 完成形運用基盤 | Actions→Cloud Build→Cloud Run・GEAP・Terraform | pushから自動デプロイ |

## ADK技術前提（google-adk 2.1.0 検証済）

- `LoopAgent(max_iterations)` は `event.actions.escalate` でループ脱出＝スコア閾値差し戻しの脱出機構。
- `LlmAgent` は `model/instruction(callable可)/output_schema/output_key/tools` を持ち、`output_schema`＋`google_search` が**共存可**。
- ⚠️ `{{var}}` 注入はトップレベルのみ（`{{a.b}}` ネスト不可→`render.py` で自前展開）。
- **結論: LangGraphフォールバックは不要**（STEP2は1モジュール隔離・差し替え口は残す）。

## 検証チェックリスト（各ゲート）

1. **C0.1**: `make verify`＋`make eval`＋`make pipeline`＋`make smoke` 緑
2. **C0.2**: v2 schema・prompt loader・dispatcher 存在。mock挙動差分ゼロ。`prompts/loader` 全11本テスト緑
3. **C1.0.1★**: MiniLoop→Langfuseで反復→escalate脱出。再実行CLI・vertex最小テスト（✅2026-06-06）
4. **コストガード**: dev＝1〜2冊/短文/Imagen mock/1R。実LLMはiterations・timeout・推定cost上限でabort
5. **C1+C3足場**: Firestore rules test・小さなMode A eval・最小CI・API最小デプロイ手順
6. **M2（C4+E2E）★**: `PUBLISHR_LLM=vertex`＋`DATA_SOURCE=firestore` でブラウザ縦通し。API Cloud Runでplanning手動トリガー1回
7. **M3（C2）**: 手動1冊→予約API→Pub/Sub worker→Scheduler自律
8. **M4（C5+B3）**: push→GEAP Evalゲート（8件・本命≥70）→自動デプロイ

## リスク・注意

- **C0.1が最初の関門**。赤い間は他作業へ進まない。
- **C1.0.1は 2026-06-06 通過済み**（grounding+schema共存・escalate脱出のランタイム実証）。次の関門は **W2 M2（C1.1–C1.3＋C4 E2E）**。詰まれば C1.3 のみ LangGraph。
- **GCPコスト暴走**: mock既定・dev縮小・実LLM上限・公開API認証が主防御。Budget通知は補助。
- **GCP齟齬**: B1.3は「無いものだけ作る」。台帳＝[gcp-setup-log.md](../infra/gcp-setup-log.md)。
- **役割**: backend/ADK/基盤＝**一瀬**、フロント/プロンプト/Eval設計/デモ＝**鉄田**。App Hosting/Cloud Build GitHub連携＝**鉄田**（組織オーナー権限あり）。

---

## 🧭 現在地サマリ（最新: 2026-06-18）

> **【2026-06-18 定例MTG・仕様変更確定】** 開発スピードは計画より前倒しで順調（Ahead of schedule）。MTGで以下のスペック変更を決定—①**入荷ロジック刷新**: 旧「週15冊（本命5+5・セレンディピティ5）・7日保持」→**新「4冊/日×週3回=12冊/週・日曜はセレンディピティ1冊のみ・過去4週間保持（最大約48冊）」**（I-29/I-17更新）。②**動的フィルタリング**: 書庫移動済みの本を入荷一覧から非表示（I-30）。③**デモ用即時入荷トリガーボタン**追加＋デモ環境ID/Password認証（I-31/I-32）。④**本文生成ボリュームのパラメータ化**（3000文字以上へ拡張・I-35）。⑤**favoriteAuthorsバグ修正**（状態保持不具合・優先度高・I-33）。⑥**GitHub公開用新規パブリックリポ作成**（PII除去・履歴クリーン・I-34）。カバー画像「青い四角」プレースホルダーは現行維持確定。現コードとの主な乖離: `arrival.ts` の `ARRIVAL_WINDOW_DAYS=7`→28日・スケジューラの入荷冊数変更・動的フィルタリング未実装。

## 🧭 現在地サマリ（履歴: 2026-06-12）

> **いまどこ（2026-06-12）**: M0〜M3完了＋M4ほぼ完了に加え、**C4.1（Google連携の一瀬バックエンド＋Drive Picker UI フロント）と C5.4/5.5（judge再現性・閾値ツール＋実Gemini judge配線）が main 入り**（PR#23・#24）＋**I-20 予約原子性transaction・C4.9 rate limit/nonce 単回化**。`make verify` **262 passed, 9 skipped**／web typecheck+lint 緑。**C4.1 は code-complete**＝BFF `routers/auth.py`（`/api/auth/google/start`・`/callback`・`/api/connect/drive-folders`）＋`oauth_service`/`token_store`(file既定/Secret Manager)/`upsert_user`、フロント `apps/web/src/lib/googlePicker.ts`＋`(auth)/connect`統合＋型＋`config` の `NEXT_PUBLIC_GOOGLE_*`。**実judge** は `eval_gate.judge_plan(backend="vertex")`＝実Gemini Pro採点(`eval_judge.md`ルーブリック・readerProfile+plan→4観点JSON)を **gated 配線**（既定mock・$0・`scripts/eval_reproducibility.py`＋`eval_threshold_sweep.py`）。**残＝①C4.1を実際に動かす＝GCPで Picker API有効化＋OAuth Webクライアント/APIキー発行＋`apphosting.yaml`に`NEXT_PUBLIC_GOOGLE_*`投入＋ブラウザQA ②実judge閾値調整＝`PUBLISHR_RUN_VERTEX=1 PUBLISHR_EVAL_BACKEND=vertex make eval-repro/eval-sweep`（課金・ADC要）で実σ/CV→`eval_set.yaml`閾値/`eval_judge.md`微調整 ③M5/M6＝デモ録画・ProtoPedia・公開リポ・最終提出7/10（鉄田主体）④別軸ハードニング＝**I-20予約原子性＋C4.9 rate limit/nonce単回化を実装済**（`reserve_book_atomic`＝mockロック/firestore `@transactional`・owner別cap・`ownerUid+status`複合index追加／`RateLimiter`(/start・/drive-folders per-uid 429)／`NonceStore`(callback replay 403)）。残＝state ブラウザ束縛(PKCE/cookie)・nonce/RLのマルチインスタンス共有ストア・I-20 emulator/live検証・mode_b vertex live・C3.3約100p+GCS ⑤小follow-up＝C1.7 serendipity・C5.1全11プロンプト実テスト・C5.3 GEAP純正運用(任意・基準5アピール)**。運用メモ: デモ垢＝佐倉 美咲(5JLL…/publishr.hackathon)。
>
> **【履歴 2026-06-11】いまどこ（実日付はW1だが進捗はM4ほぼ完了＝計画より約3週 前倒し）**: **M0/M1/M2★/M3 完了＋M4ほぼ完了**。モードA（観測→企画→キャスティング→プレビュー→装丁→入荷）＋モードB（予約→Pub/Sub→worker→本文編集ループ 最高3R→published）＋**C1.7 Scheduler本番（自律入荷）**が **ローカル完走＋クラウド（Cloud Run/Firestore/Pub/Sub/Scheduler）疎通済み**で main 入り。3つの必然性ループ（調査grounding・企画リーダー差し戻し・編集長本文差し戻し）が揃った。`make verify` **210 passed, 8 skipped**。直近マージ＝PR#1〜#17（…**PR#13 B4.1 IaC**・**PR#15 M4品質ゲート C5.9/C5.6/C5.3+CI**・**PR#17 B3.2 CD自動デプロイ**）。**M4ほぼ✅＝B4.1 IaC＋C5.9＋C5.6＋C5.3＋B3.1 CI＋B3.2 CD（mainマージ→verify→Cloud Run自動デプロイ・WIF・実機00007検証✅）**。**残＝① M4＝C5.3 GEAP本番judge(課金)/C5.4-5.5 judge再現性・閾値調整（鉄田と）② M5/M6＝デモ録画・ProtoPedia・公開リポ・最終提出7/10（鉄田主体）③ C1.7 serendipity(日)差別化の小follow-up**。**C4.1 Google連携ページ（UIのOAuth/Drive Picker）は依然🔴未（鉄田）**＝connect はモックトグルのみ・Picker/BFF OAuth endpoint 無し（観測用OAuthはCLI task#7 L1=calendar+tasks のみ実動）。**運用メモ: デモ垢＝佐倉 美咲(5JLL…/publishr.hackathon)・Cloud Run DEMO_UID も5JLLに更新済**（旧記録の「佐倉=WW1j」は誤り＝WW1jは鉄田垢）。別軸ハードニング＝C4前セキュリティ(C4.9)/I-20予約原子性transaction/mode_b vertex live/約100p+GCS保存(C3.3)。

> **【履歴 2026-06-07】いまどこ**: **C0.1/C0.2/B1.3/C1.0.1 完了→次は C1.1–C1.6＋C3.x＋B3.1（W1）**。mock/canned の回帰床（`make verify`＋`make eval`＋`make pipeline`）は緑（pytest **60 passed, 1 skipped**・**2026-06-07にペルソナ不整合の回帰=I-24を解消**。make smoke は Windows の OpenSSL/POSIX 環境問題で本機未実行）。**C1.0.1（H2 MiniLoop）**＝実Vertexで `market_sub(Flash+google_search)→Loop[max3](owner→leader→LoopBreakAgent)` の escalate 脱出を実証済み（threshold70→R1 approve／threshold101→R1 revise→R2 approve）。再実行CLI＝`scripts/run_miniloop.py`・Langfuse計装＝`observability.py`（SDK直・best-effort）・`@pytest.mark.vertex` 最小テストあり。設計・プロンプト・Eval・GCP基盤・OAuth認証が整い、**フロント16ルート(mock)＋ADK配線骨格(`agents/`・canned出力)＋BFF mock API(`apps/api`)** まで先行実装済み。**友人MTG（2026-06-05）完了＝着手前ゲートを全件クローズ**。次の山場は **C1.1–C1.3「E2E縦通し＝実モデル＋v2 I/O」(W2)**。W1並行＝**B3.3 App Hosting連携（鉄田）**・**C5.1 プロンプト実テスト**。**実装順序は本書 §エージェント実施ガイド の WBS 直列表に従う**。
>
> **【2026-06-07 フロントUI仕上げ（C4.8）✅完了】** **2026-06-06実施**: 読書画面を中心に複数の UI 改修：①**読書ページ再構成**＝ハイライト一覧ページ(`/read/[bookId]/highlights`)・目次ページ(`/read/[bookId]/contents`)を新規作成し読書ページサイドバーをナビ3リンク（目次・ハイライト・本の概要）に改修、`?pi`/`?ch` クエリパラメータによる本文ジャンプ機能を実装 ②**KindleライクなハイライトUX**＝ドラッグで範囲指定→自動ハイライト、クリックで色変更(黄/青/ピンク)＋削除ポップアップ（`ReadingAnnotation.startOffset/endOffset` で文字単位記録） ③**目次・本の概要の統一**＝`bookChapters(book.body)` で本文Markdownから実際の章を導出する`BookToc`共有コンポーネント新設（目次ページ・本の概要ページで共用）、本の概要ページからフル版/要約版/ここだけトグルと「今朝入荷」バッジを削除 ④**書庫サイドバー改善**＝ラベルを「最近読んだ本」に変更・published本のみ最大5件・著者名非表示 ⑤**書庫ページ表紙デザイン強化**＝`midnight/forest/slate/rust/wine/ink` 各バリアントに CSS `::before` 装飾（円弧・縦ライン・数字透かし等）を追加し書店ページ(`b1`〜`b10`)と同等の視覚的リッチさに統一。**2026-06-07実施**: ①**フィードバックチップ修正**＝ページロード時に非表示・いいね/いまいちタップで展開（`{reaction && ...}` 条件付きレンダリング） ②**ナビカードジャンプ修正**＝`.rail-tools` の `position:sticky` を廃止しグリッド上端固定（`navDelta:0` を eval 実測で確認） ③**🔔通知ベル＋ドロップダウンパネル** 新設（`NotificationBell.tsx`）＝入荷/執筆完了/お気に入り作家の3種・未読バッジ・全既読ボタン・各通知から`/books/{bookId}`概要ページへリンク ④`AppNotification`型・`BaseProvider` 通知API（`pushNotification`/`markNotificationRead`/`markAllNotificationsRead`等）・`MockProvider` の `seedNotifications`（決定的シード3件）＋`reserve`完了時自動通知 ⑤`useNotifications`/`notifyFavoriteAuthor` フック ⑥読了ページ・書籍概要ページのTopbarをデフォルトベルに統一。**C4.8 機能実装＋デザイン・完了**（Firestore本接続後の全画面QA = C4.9 依存のみ残）。
>
> **【2026-06-07 セッション2＝フロント登録導線・初回体験・本番データ整備】** firestoreモード（本番）でアカウント検証中の不具合修正＋初回体験実装＋データ整理（実LLM/パイプライン非介入）。①**表示名をFirebase Authログインユーザーに統一**（トップ挨拶・サイドバー・アカウント）＋デモ残骸一掃（ハイライトseed非表示・統計実数化・データ連携を初期未連携トグル化）②**初期設定にserendipity追加＋アカウントに読み口表示/編集**（双方向整合）③**オンボーディング登録ボタンの固まり解消**＝`saveInitialProfile`のlocalStorageキャッシュ＋Firestore非throw化・登録後トップ`/`遷移・アカウント即反映 ④**ログイン時に初期設定済みならオンボーディングをスキップ**（`hasCompletedOnboarding`・Firestore優先）⑤**初回体験「空→生成中→15冊」をmockで実装**（`firstRunCatalog.ts`本命10＋セレンディピティ5・`runFirstRun`・生成中UI＋45秒安全タイムアウト＋手動スキップ・**firestore実生成はC1依存で未＝I-22**）⑥**Firestoreルールを本人のinitialProfile書込許可に緩和・再デプロイ**（旧「初回のみ」制約が登録を黙って失敗させていた・I-6）⑦**ローカルサンドボックス整備**（`dev:mock`/`dev:emulator`＋Firebaseエミュレータ＋Java・`docs/infra/local-sandbox.md`・B2.2前進）⑧**本番Firestoreテストデータ整理**（孤児book/レガシーuser削除・鉄田佐倉name修正）＋運用スクリプト4本（I-14前進）。⑨**デモペルソナを佐倉美咲に全面統一しtest-py(C0.1)を復旧**＝`91d3282`がusers.jsonだけ佐倉化→backend/テストが田所のまま赤だったのを keep_notes/canned.py/fixtures/tests/eval_harness 全面再オーサリング（`3e4b03b`・**60 passed,1 skipped**）。新規論点＝**I-22**（初回15冊の実生成未実装）・**I-24**（91d3282由来のtest-py赤＝✅解消）。なお当初起票の**I-23（lint赤）は誤認＝実際は緑**。コミット `25f57c6`〜`3e4b03b`。
>
> **✅ できている（土台）**
> - 設計docs一式／完成プロンプト11本（`packages/prompts/`）／Eval Set 8件（`eval/eval_set.yaml`）
> - GCP基盤（`publishr-498123`：Firestore/Storage/SA/Secret Manager/Firebase/予算アラート）— **2026-06-06に実態確認済**（[gcp-setup-log.md](../infra/gcp-setup-log.md)・B1.3）。Vertex Gemini 疎通スモーク成功（ADC・asia-northeast1）
> - **【2026-06-04完了】GCP IAM 2人招待・OAuth同意画面(Production)・テストユーザー・OAuthクライアント`Publishr Web`発行・GitHub Secrets 計6本**（GCP_PROJECT_ID／GCP_SA_KEY／GOOGLE_OAUTH_CLIENT_ID／SECRET／LANGFUSE×2）※Secret Manager 側は Langfuse 3本のみ実在（OAuth 2本は gap・要登録 or GitHub Secrets 住み分け明記）
> - GitHubリポ（**2026-06-05に組織アカウント `cloud-dojo` へ移管完了→`cloud-dojo/publishr`・鉄田もオーナー権限付与済**）／モノレポscaffold（agents・apps・packages・eval・docs）／計画docsをrepoへ統合
>
> **【2026-06-06完了・C0】**
> - **C0.1（mock回帰復旧）**: `make verify`（pytest 58 passed, 1 skipped）＋`make eval`（8件PASS）＋`make pipeline`＋`make smoke` が全緑。`eval/eval_set.yaml`（v2）と `scripts/eval_harness.py` の不整合を解消
> - **C0.2（実装シーム敷設）**: v2 I/O schema（`packages/shared-schema/py/publishr_schema/agent_io.py`）・state keys・prompt loader/registry/render・LLM provider・`PUBLISHR_LLM` dispatcher・dev/prod実行プロファイル・実LLMコストガード＋単体テスト。mock経路の挙動差分ゼロ
>
> **【2026-06-06完了・C1.0.1（H2）】**
> - **C1.0.1（ADK MiniLoop・実Vertex escalate実証）**: `agents/publishr_agents/vertex/miniloop.py` 新設。`Sequential[market_sub(Flash+google_search)→Loop(max3)[plan_owner→plan_leader→LoopBreakAgent]]`。score<閾値→`rejectionFeedback`再ループ／score≥閾値→`escalate`脱出／round3強制承認（prompt+code帯）。H2実証＝threshold70→R1 approve(93) escalate脱出／threshold101→R1 revise(98)→R2 approve。grounding実取得・ownerがsub参照・Langfuse trace送信（`observability.py`・SDK直・best-effort）。再実行CLI＝`scripts/run_miniloop.py`（`--threshold`で差し戻し誘発）・`@pytest.mark.vertex` 最小テスト（`agents/tests/test_miniloop_vertex.py`・既定skip＋offline build test）。prompt loader/render も ADK State 対応で修正（`load_section_system`・`render_template`公開）
>
> **【2026-06-04完了・鉄田単独タスク】** initialProfile選択肢リスト(G1-9・A3.2)✅／gcloud CLI×Norton 恒久対処(G1-20)✅／デモはカット割り廃止＝**動画台本2本立て**(2.5分=審査提出用／60秒=ピッチ内・C6)へ置換✅
>
> **【フロント・backend とも mock/canned で先行実装済】** `apps/web`(Next.js) に書店UI **16ルートを mock で実装（ビルド緑・C4 code-complete・当初14＋C4.5で読書サブ2追加）**／Firebase Auth＋Firestoreプロバイダも実装済（mock時休眠）。**backend も「未着手」ではなく**、`agents/publishr_agents`（実ADKの Sequential/Parallel 配線・**出力は決定的canned**・選抜ゲートの差し戻しログも canned・`test_pipeline.py`あり・**PUBLISHR_LLM dispatcher 済**）と `apps/api`（FastAPI BFF＝books/plans/personas/users/pipeline ＋ reservation/feedback/reading サービス＋`mock_repository`）が main にある。**ただし backend は v2フローの簡略版**（調査サブ×3 grounding・キャスティング5人2軸・プレビュー編集ループ・実escalate・5冊transaction は未）。残＝**①UI仕上げ(C4.8) ②Firestore本接続(C4.9・一瀬待ち) ~~③App Hosting連携(B3.3)~~ →✅2026-06-06完了 ③canned/mock→実LLM・実Firestore差し替え(C1.x/C2.x/C3.5)**。公開URL=`publishr--publishr-498123.asia-east1.hosted.app`。
>
> **【提出物・GEAP方針・2026-06-05】** ProtoPedia作品ページ草案一式（ストーリー約4,000字・画像5＋システム構成図・全フィールド記入シート）を作成＝対外 `publishr_other/Protopedia提出/`（WBS **C6.7/C6.8**・P-6/P-7）。**GEAP（旧Vertex AI）はプラスアルファで②Gen AI Evaluation Service を品質ゲートに採用方針**（動くコード済・I-21/**C5.3**）、④Agent Runtimeはストレッチ（Schedulerトリガー非対応・F-7）。
>
> **✅ 着手前ゲートはMTG 2026-06-05で全件クローズ（A5.1完了）**
> - **友人MTG（2026-06-05実施・完了）**: ADK実現性(G1-1=一旦これでいくで合意)・役割分担(G1-2=基本合意／基盤Firebaseのみ担当未定)・**Drive Picker(G1-13=フォルダ単位・Picker前提で確定)**・Cloud Build接続(G1-18=方式A・組織化で確定)・OAuth公開ステータス(G1-19=Production維持)・通知方式(G1-15=FCM不要)を握った。Langfuse実装方式(G1-17)は全体設計は先送りだが、**MiniLoopは Langfuse SDK直で暫定実装済**（`observability.py`・C1.0.1）
>   - **＋ 設計/データの確定（叩き台のまま即確定）**: 観測束ObservationBundleの保存先(I-19)／API CORS・ベースパス(G1-7)／手動トリガー認可(G1-6)／読書ログ集約(I-9)／予約の原子性・冪等(I-20) を**全て確定**。詳細は [open-issues.md](open-issues.md) と当日アジェンダ §3-4〜3-6
> - **環境の積み残し**: OAuth本番リダイレクトURI追記（backendデプロイ後・B1.2／現状は仮の`localhost`のみ）
> - **フロント本番ホスティング（B3.3・G1-7）**: ✅**2026-06-06完了**。Firebase App Hosting＋Next.js(`apps/web`)でmock公開済。公開URL=`publishr--publishr-498123.asia-east1.hosted.app`（build-010成功）。Turbopack×npm workspaces問題を解消し自動デプロイ稼働中。
> - **フロント本接続の前提（C4.9・一瀬から受領）**: フロントは mock 実装済→本接続には一瀬から ①**Firebase Web設定値**(`NEXT_PUBLIC_FIREBASE_*`) ~~②**Firestoreセキュリティルールのデプロイ**→✅**C3.1完了済み（2026-06-06・鉄田）**~~ ③**Cloud Run API 3本**(reserve/OAuth/trigger)の**URL・CORS** ④**Firestore docが`@publishr/shared-schema`形で保存・`ownerUid`規約**の握り、が必要。受領後 `NEXT_PUBLIC_DATA_SOURCE=firestore` で本接続
> - **【2026-06-06完了・鉄田C3巻取り】** **C3.1** Firestoreセキュリティルール本番デプロイ（firebase.json/.firebaserc/firestore.rules/firestore.indexes.json）✅ **C3.4** 観測ログサブコレクションルール（C3.1に内包）✅ **C3.5** BFF FirestoreRepository実装（`apps/api/publishr_api/repositories/firestore_repository.py`・firebase-admin追加・DATA_SOURCE=firestore切替・テスト11件グリーン）✅。C3全体の担当を一瀬→**鉄田**へ変更。C4.9の②依存は解消。

---

## 日次ログ（ざっくり・2026-06-06〜09）

> W0（6/1–7）の締め2日。**鉄田＋エージェント作業**。クラウド課金は **C1.0.1 の MiniLoop 手動実行時のみ**（`PUBLISHR_LLM=vertex`）。mock床・放置中のローカル dev は課金なし。
> ※新しい日付を上に追記。

### 2026-06-09（火・一瀬）— M2 縦通し（バックエンド側）達成

| 領域 | やったこと | WBS |
|---|---|---|
| **C1.1** | task#7 Google live観測 **L1**（calendar+tasks 実OAuth→ObservationBundle）。`drive.readonly` は restricted で除外、`PUBLISHR_GOOGLE_SCOPES` で切替 | C1.1 |
| **C4/BFF** | `POST /api/trigger/planning` を旧canned→**新モードA**差替（観測→…→装丁→arrivals永続）。`trigger_guard`（許可uid/レート/実行中ロック）。reject_log=却下→採用 | C4.9系 |
| **M2** | **最小Cloud Run疎通**（BFF mock）→ **firestoreモード切替**（実SA `publishr-runner`）。Cloud Run trigger→実Firestoreの佐倉arrivals書込（`booksAdded=5`・owner佐倉・却下→採用）を確認＝**M2縦通し達成**。デプロイ済WebはFirestore直読みで反映 | M2★ |
| **検証** | `make verify` 170 passed,7 skipped。PR#4 main マージ（origin/main=afd3c96） | — |

**✅ ブラウザボタン配線（一瀬で自己完結・2026-06-09）**
- 発見: `apps/web/apphosting.yaml`（App Hosting が読む方）に既に `NEXT_PUBLIC_DATA_SOURCE=firestore`＋`NEXT_PUBLIC_API_URL` が設定済みだったが、**URL が死んでた asia-east1（404）**を指していた。BFF 実体は asia-northeast1。
- 修正: `apphosting.yaml` の `NEXT_PUBLIC_API_URL` を **`https://publishr-api-355143691286.asia-northeast1.run.app`** に修正（`apps/web/src/data/config.ts:9` が読む変数）。live branch=main へ push → App Hosting 自動再ビルド。鉄田のセットアップ作業は不要だった（env1行の修正＝通常のリポジトリ変更）。
- UI導線: `page.tsx:67 runFirstRun → firestore-provider.ts:134 runPipeline → POST /api/trigger/planning`。
- 契約: `POST {API_URL}/api/trigger/planning` body `{ "userId": "u_sakura" }` ＋ Firebase IDトークンを `Authorization: Bearer`。返り `{ ok, booksAdded }`。CORS は App Hosting本番ドメイン許可済み。
- 確認: 再ビルド後、佐倉ログインで初回生成導線→Cloud Run BFF→入荷反映。連打は `429`。
- 一瀬判断待ち2点（任意）: ①入荷テーマ＝現在トリガー出力「役員中間報告…」。以前の「新任マネージャー…」見出しに戻すなら `DATA_SOURCE=firestore uv run python -m scripts.seed_arrivals --owner-uid WW1j4mkYC0VzuzDdQ0OQ4Ff8zFd2 --theme "新任マネージャーの任せ方・権限委譲（年上の実力者部下を含む）" --apply`。②録画時のみ Cloud Run を `PUBLISHR_LLM=vertex` に（実LLM生成・課金）。
- 本番ハードニング（トークンfail-closed・owner厳格化・vertex時allowlist必須・マルチインスタンスrate limit）は **C4.9 / G1-21** に集約。

### 2026-06-06（土）

| 領域 | やったこと | WBS |
|---|---|---|
| **C0** | **C0.2 完了** — v2 I/O schema・prompt loader/registry/render・`PUBLISHR_LLM` dispatcher・dev/prod実行プロファイル・コストガード。mock挙動差分ゼロ | C0.2 |
| **B** | **B1.3 完了** — GCP runbook 追加→STEP A 実態確認→Vertex Gemini 疎通スモーク成功。台帳 `gcp-setup-log.md` 更新（gap＝OAuth Secrets 未登録は残） | B1.3 |
| **設計/docs** | `security-data-handling.md` 新設。Cloud Run 公開前ゲート（G1-21）方針確定。旧 Phase 表記を WBS ID へ置換開始 | A2/B1 |
| **C1** | **C1.0.1（H2）完了** — 実Vertex MiniLoop（調査サブ＋owner/leader Loop＋escalate）。`run_miniloop.py`・`observability.py`（Langfuse SDK）・`test_miniloop_vertex.py`。差し戻し→再提出→採用を実証（threshold 操作で両パターン確認） | C1.0.1 |
| **検証** | mock床 全緑 — `make verify`（58 passed, 1 skipped）／`make eval`／`make pipeline`／`make smoke` | C0.1 |

### 2026-06-07（日）

| 領域 | やったこと | WBS |
|---|---|---|
| **docs** | **WBS 正本を 2026-06-07 版に更新** — C1.0.1 完了・M1 前倒し達成・次着手＝C1.1以降を明記。`docs-replicated-bonbon.md` を wbs への移管案内に整理。infra 台帳/runbook の Phase→WBS ID 統一 | 全体 |
| **C0** | P0b 残りを補完 — `runtime.py`（コストガード）・`.env.example` 実行プロファイル項目・BFF `config.py` ＋単体テスト | C0.2 |
| **運用** | ローカル dev サーバ（uvicorn/next）が数日分残存していることを確認。**GCP課金は発生していない**（`PUBLISHR_LLM=mock` 既定） | — |
| **C4.8** | **UI仕上げ完了**（機能実装＋デザイン） — ①フィードバックチップ修正（ページ初期=非表示・タップで展開、`{reaction && ...}` 条件付きレンダリング）②ナビカードジャンプ修正（`.rail-tools`のsticky廃止、`navDelta:0`実測確認）③🔔通知ベル＋ドロップダウンパネル新設（`NotificationBell.tsx`・入荷/執筆完了/お気に入り作家の3種・未読バッジ・全既読・各通知→`/books/{bookId}`）④`AppNotification`型・BaseProvider通知API・MockProvider seedNotifications/reserve完了通知⑤`useNotifications`/`notifyFavoriteAuthor`フック⑥読了ページ・書籍概要ページTopbarにデフォルトベル統一。`NEXT_PUBLIC_DATA_SOURCE=mock` に復元（`.env.local`） | C4.8 |
| **docs** | WBS 更新 — C4.8 ✅完了・日次ログ追記 | 全体 |
| **C1.1** | **STEP0 観測ツール 実装（live検証残）** — `agents/publishr_agents/observe/`（純粋transform＋`FixtureObservationSource`既定＋`GoogleObservationSource`隔離・`PUBLISHR_OBSERVE`切替）。型付き`ObservationBundle`/`ConnectedSources`をschema(py/ts)へ。CLI`run_observe.py`＋`google_oauth_bootstrap.py`、`@pytest.mark.google`。±14日窓/4000字/Tasks絞り/folderIdスコープをtransform一元化。**masked回帰も修正**＝`91d3282`で消えた`u_tadokoro`をusers.jsonへ復元（canned pipeline緑化）＋test_fixtures整合。`make verify`(84 passed,2 skipped)/eval/pipeline/smoke 緑。残＝OAuth同意→実3ソースのlive検証。ブランチ`feat/c1.1-step0-observation` | C1.1 |
| **C1.2** | **STEP1 読者分析 実装＋実Vertex live実証** — `agents/publishr_agents/reader/`（`deterministic.py`既定＋`vertex_agent.py`実Gemini Pro＋`__init__`=PUBLISHR_LLM dispatch）。step1プロンプト/registry/model_for(Pro)結線。CLI`run_reader.py`（STEP0→STEP1縦串）。**live実証**＝fixture観測→実Pro→3層ReaderProfile（佐藤健一/競合A社/田中健太まで踏込・evidence紐付き）。`make verify` pytest 95 passed,3 skipped・typecheck緑（web lintはmain既存1件のみ）。同ブランチ継続 | C1.2 |
| **C1.6** | **STEP5 装丁 実装＋実Imagen live実証（モードA STEP0→5 完成）** — `agents/publishr_agents/cover/`（`deterministic.py`=coverVariant(CSS)＋canned prompt／`vertex_agent.py`=Flash coverPrompt／`imagen.py`=実Imagen(imagen-3.0・us-central1)→PNG→coverUrl／`__init__`=PUBLISHR_LLM＋ENABLE_IMAGEN）。CLI`run_mode_a.py`（STEP0→5 完全縦串）。live: 実表紙2枚生成（`.dev-logs/covers/`・896×1280・著者軸で作風差別化・文字焼かず）。`make verify` pytest 136 passed,7 skipped・typecheck緑。code-review Approve。同ブランチ継続 | C1.6 |
| **C1.5** | **STEP4 プレビュー編集 実装＋実Vertex live実証（モードA縦串 完走）** — `agents/publishr_agents/preview/`（`deterministic.py`＝5冊BookDraft(7項目)＋編集長1R実演／`vertex_agent.py`＝author/editor Pro を Pythonで著者→編集長→1R改稿・`limit`／`__init__`=dispatch）。CLI`run_preview.py`（**STEP0→1→2→3→4 フル縦串＝棚5冊draft**・段階別LLM切替）。mock で5冊draft完走、live で STEP4 2冊（「7人の意思決定を、設計しなさい。」「あなたのいない会議室で」＝観測grounded・著者で作風差別化）。`make verify` pytest 127 passed,6 skipped・typecheck緑。code-review Approve。同ブランチ継続 | C1.5 |
| **C1.4** | **STEP3 キャスティング 実装＋実Vertex live実証** — `agents/publishr_agents/casting/`（`deterministic.py`既定＝5著者を voiceStyle×format 2軸で分散・favorite 1枠／`vertex_agent.py`＝persona_generator Pro・output_schema=GeneratedPersonaSet／`__init__`=PUBLISHR_LLM dispatch）。CLI`run_casting.py`（STEP0→1→2→3 縦串）。live: 実Proで5著者2軸分散を確認（gated test・Pro1コール）。`make verify` pytest 117 passed,5 skipped・typecheck緑。code-review Approve（LOW2点反映）。同ブランチ継続 | C1.4 |
| **C1.3** | **STEP2 企画3階層 実装＋実Vertex live実証（必然性の本丸）** — `agents/publishr_agents/planning/`（`deterministic.py`既定＝3サブ→owner→leaderループ reject→approve trace／`vertex_agent.py`＝`Sequential[Parallel[3サブ]→Loop[owner→leader→miniloop.LoopBreakAgent]]`・miniloop不変で再利用／`__init__`=PUBLISHR_LLM dispatch）。CLI`run_planning.py`（STEP0→1→2縦串・`--llm`/`--reader-llm`/`--theme`/`--threshold`）。**live実証2回**: ①threshold85→R1 approve(97) escalate脱出・観測grounded企画 ②threshold101→R1 revise(98)→R2 approve(102)＝差し戻し理由「失敗談で差別化」をR2が実反映＝reject→再提出の必然性。3サブB/Cは実Google検索grounding。`make verify` pytest 107 passed,4 skipped・typecheck緑。code-review Approve（M1 serendipityテーマ導出を修正反映）。同ブランチ継続 | C1.3 |

### 2026-06-07（日・セッション2＝フロント登録導線・初回体験・本番データ整備）

> firestoreモード（本番App Hosting）でアカウント（鉄田・佐倉）を作って検証中に発覚した不具合修正＋初回体験の実装＋本番テストデータ整理。**実LLM/実パイプラインは触らず**、フロント＋Firestoreデータ運用のみ（GCP課金なし）。コミット `25f57c6`〜`9cab2d7`・push済み・本番反映済み。

| 領域 | やったこと | WBS |
|---|---|---|
| **C4（表示名/残骸）** | ①トップ挨拶・サイドバー・アカウントの**表示名をFirebase Authログインユーザーに統一**（fixtures固定→ログインユーザー）②デモ残骸一掃＝ハイライトseedをログイン時非表示・統計を実数化・お気に入りをuid別hydrate・注記バナー削除・データ連携を**初期未連携トグル**化 | C4.1/C4.8 |
| **C4（プロフィール）** | ③初期設定に**「新しい出会いの幅」(serendipity)ステップ追加**＋アカウントに**「好みの読み口」(readingGenres)表示/編集**を追加（初期設定⇔アカウントの双方向整合） | C4.1 |
| **C4（オンボーディング）** | ④**登録ボタンの固まり解消**＝`saveInitialProfile`をlocalStorageキャッシュ＋Firestore非throw化、`persist`をtry/catch化し登録後トップ`/`へ直接遷移・アカウント即反映 ⑤**ログイン時に初期設定済みならオンボーディングをスキップ**＝`hasCompletedOnboarding()`（Firestore優先・localStorageフォールバック） | C4.1 |
| **C4（初回体験・Part B）** | ⑥**「空→生成中→15冊」初回体験をmockで実装**＝`firstRunCatalog.ts`（本命10＋セレンディピティ5）・`provider.runFirstRun`（mock=時間差入荷／firestore=既定runPipeline）・生成中UI（スケルトン＋スピナー＋進捗＋45秒安全タイムアウト＋手動スキップ）・`firstRunStatus`(localStorage)。**mockで15冊順次入荷→完成までフル動作を確認**。**firestoreの実15冊生成はC1依存で未**（I-22） | C4.2/C1依存 |
| **C3.1** | ⑦Firestoreルールを**本人がinitialProfileを書ける**よう緩和（旧「初回のみ」制約が登録・プロフィール編集をpermission deniedで黙って失敗させていた）→再デプロイ | C3.1/I-6 |
| **B2.2** | ⑧**ローカルサンドボックス整備**＝`dev:mock`（mock・認証なし）／`dev:emulator`＋`emulators`（Firebase Auth/Firestoreエミュレータ）・firebase.json/firebase.ts配線・Javaインストール・手順書`docs/infra/local-sandbox.md`。本番ビルドに頼らず高速反復可能に | B2.2 |
| **C6.2/データ** | ⑨本番Firestoreのテストデータ整理＝孤児book(`b_kikitai`/`b_ringi`)・レガシーuser(`u_tadokoro`)削除、鉄田/佐倉の`name`修正 ⑩Firestore運用スクリプト4本（`inspect_firestore`/`cleanup_firestore`/`fix_user_name`/`patch_book_bodies`＝存在チェック追加で孤児再生成防止）整備 | C6.2/I-14 |

### 2026-06-08（月・一瀬＝モードA全STEP実装〜画面結線）

| 領域 | やったこと | WBS |
|---|---|---|
| **C1.1–C1.6** | **モードA企画パイプライン全STEP実装**（観測→読者→企画3階層→キャスティング→プレビュー→装丁）。各STEP＝決定的mock既定＋実Vertex隔離・TDD・code-review・live実証。`run_mode_a.py` で STEP0→5 縦串。実Imagen表紙2枚も生成。PR #1 で main マージ | C1.1〜C1.6 |
| **C1.7** | **自律トリガー（曜日別・ローカル/mock・課金ゼロ）**。`scheduler.py`（水/土=本命・日=セレンディピティ）＋`run_scheduler.py`（--once/--watch）。PR #2 で main マージ | C1.7 |
| **C4結線** | **モードA成果→Firestore→書店arrivals**。`persist_mapping.py`（v2出力→Book[arrivals/draft/ownerUid]＋Persona）・`upsert_persona`をRepositoryProtocol/mock/firestoreへ追加・`seed_arrivals.py`（mock生成→map→upsert・dry-run既定）。**共有Firestoreへ佐倉の入荷5冊＋著者を live投入**（mock＝LLM課金ゼロ・新規`arr_*`ID・非破壊）。書店トップに実5冊が並ぶ状態に。残＝Plan永続化(detail panel)・BFF trigger差替・本番Scheduler | C4.9系 |

**W0の成果（2日で通したゲート）**: C0.1 → C0.2 → B1.3 → **C1.0.1★**（M1 前倒し）。**W1（6/8〜）の最初の山**＝C1.1 観測 ＋ B3.3 App Hosting 連携。

---

## WBS 全体ツリー（カテゴリ主役）
```
Publishr MVP（カテゴリWBS）
├─ A. 要件定義・設計            … 何を作るか（ほぼ✅完了）
│   ├─ A1 構想・MVPスコープ
│   ├─ A2 アーキ・I/O契約・API・データモデル設計
│   ├─ A3 プロンプト・判断基準設計
│   ├─ A4 Evalセット・品質基準設計
│   └─ A5 共有スキーマ正本確定／着手ゲート(友人MTG)
├─ B. 環境・インフラ構築          … 動かす土台（GCP本体✅・B1.3確認済・CI/ホスティングはW1〜）
│   ├─ B1 GCP基盤・認証（IAM/OAuth/Secrets）  ← Google Cloud系=鉄田
│   ├─ B2 リポ・モノレポ・ローカル環境
│   ├─ B3 CI/CD・ホスティング（Actions/Cloud Build/App Hosting）  ← 鉄田がGitHub連携を実施（組織移管・オーナー権限完了）
│   └─ B4 IaC（Terraform）
└─ C. 実装                   … コーディング本体
    ├─ C0 ローカル基盤固め  … mock回帰(C0.1)＋実装シーム(C0.2)（✅2026-06-06完了）
    ├─ C1 エージェント・モードA（自律企画）★ ← STEPでレベル3展開（一瀬）
    │   ├─ C1.0 ADK基盤・疎通(MiniLoop)（✅C1.0.1完了・2026-06-06）
    │   ├─ C1.1 STEP0 観測
    │   ├─ C1.2 STEP1 読者分析
    │   ├─ C1.3 STEP2 企画3階層（調査サブ→担当者→リーダー）
    │   ├─ C1.4 STEP3 キャスティング
    │   ├─ C1.5 STEP4 プレビュー編集
    │   ├─ C1.6 STEP5 装丁
    │   └─ C1.7 自律トリガー(Scheduler)
    ├─ C2 エージェント・モードB（後追い執筆）（一瀬）
    ├─ C3 データ/状態基盤（Firestore/GCS）（**鉄田**へ巻取り・一瀬外れ）
    ├─ C4 フロント（書店UI・16ルート）（鉄田）
    ├─ C5 品質・評価・観測・運用（Eval/Langfuse/コスト）
    └─ C6 デモ・提出物（鉄田）
```

> **読み方**: 大分類は3つ（A=決める／B=土台／C=作る）。実装(C)はエージェントSTEP単位で内部分解。各表の「予定週」列が時間軸で、章立て（カテゴリ）は週から独立。各DoD末尾の `(旧WPx.y)` は旧・週次版WBSの参照ID。

---

# A. 要件定義・設計

> 何を作るか・どう作るかの確定。**大半は✅済**（着手ゲート＝友人MTGは2026-06-05完了・共有スキーマ正本の置き場所も確定）。詳細は `docs/design/*.md`。

## A1. 構想・MVPスコープ
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| A1.1 | 構想・新規性・コア価値・UX設計 | このサービスが何者で、なぜ新しいのか（指示しなくても本を企画・出版するAI出版社）を文章で固める土台ドキュメント | 鉄田 | — | — | [concept-summary.md](../design/concept-summary.md) 確定 (旧WP—) | ✅完了 |
| A1.2 | MVPスコープ・IN/OUT・審査基準対応 | ハッカソンで「作るもの／作らないもの」の線引きと、審査基準1〜5への対応を決める | 鉄田 | — | — | [mvp-scope.md](../design/mvp-scope.md) 確定 | ✅完了 |

## A2. アーキ・I/O契約・API・データモデル設計
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| A2.1 | 技術アーキ・2モード分離・GCPマッピング | どの技術（Cloud Run/Firestore/ADK等）をどう組み合わせるか全体図を描く設計書 | 鉄田・一瀬 | — | — | [tech-architecture.md](../design/tech-architecture.md) | ✅完了 |
| A2.2 | エージェントI/O契約・プロンプト骨子 | 各AIが「何を受け取り何を返すか」の入出力ルール（実装の仕様書）を決める | 鉄田 | — | — | [agent-io-contract.md](../design/agent-io-contract.md) STEP0-5確定 | ✅完了 |
| A2.3 | ADK制御フロー・state管理・エージェント木 | AIたちをどの順番で動かし、やり直し（ループ）をどう制御するかの流れ設計 | 鉄田・一瀬 | — | — | [adk-control-flow.md](../design/adk-control-flow.md) | ✅完了 |
| A2.4 | フロント⇔バックAPI契約 | 画面とサーバーが通信する窓口（予約・ログイン・起動）の仕様を決める | 鉄田・一瀬 | — | — | [api-contract.md](../design/api-contract.md) | ✅完了 |
| A2.5 | Firestoreデータモデル・セキュリティルール設計 | データベースにどんな形でデータを保存し、誰が読み書きできるかのルールを設計（デプロイはC3.1） | 一瀬 | — | — | [firestore-security-rules.md](../design/firestore-security-rules.md) | ✅完了 |

## A3. プロンプト・判断基準設計
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| A3.1 | 完成プロンプト＋良い/悪い例（11本） | 各AIへの「指示文」と良い例・悪い例を作る（AIの中身の質を決める核）。実テストはC5.1 | 鉄田 | — | — | `packages/prompts` (旧WP5.1) | ✅完了 |
| A3.2 | initialProfile 選択肢リスト確定 | ユーザー登録時に選ぶ選択肢（業界13/職種11/役職7/関心19/読み口7）のリストを決める | 鉄田 | —（✅6/4完了） | — | `apps/web/src/data/profileOptions.ts`（正本・G1-9） (旧WP5.2) | ✅**2026-06-04完了** |

## A4. Evalセット・品質基準設計
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| A4.1 | Eval Set 8件（v2・3層/8項目/0-100/4観点） | AIの出力品質を自動採点するためのテスト問題集8件を作る。再現性テストはC5.4 | 鉄田 | — | — | `eval/eval_set.yaml` (旧WP7.1) | ✅完了 |

## A5. 共有スキーマ正本確定／着手ゲート
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| A5.1 | 友人MTG（チェックリスト§1の全議題を握る） | 2人で役割分担・技術の実現性・未決事項・相互の権限状態を最終確認する打ち合わせ | 鉄田・一瀬 | W0（6/1–7） | — | マイルストーン・役割・G系(Picker/通知/Cloud Build方式/OAuth)合意／**設計・データ決定(観測束保存先I-19・CORS/ベースパスG1-7・トリガー認可G1-6・読書ログ集約I-9・予約原子性I-20)を全て確定**。Langfuse実装方式(G1-17)のみ先送り (旧WP0.1) | ✅**2026-06-05 実施・完了** |
| A5.2 | 共有スキーマの正本確定＋packages/prompts投入 | Python/TS/JSONでデータの「型」定義を1か所に統一し、2人のコードで食い違いを防ぐ | 鉄田・一瀬 | W1（6/8–14） | A5.1 | 型ドリフト防止の単一ソース（G1-11）。prompts投入✅／正本＝`packages/shared-schema`（`@publishr/shared-schema`）に置く方針をMTG 2026-06-05で確定／**v2 I/Oモデル（`agent_io.py`）＋fixtures/models 肉付けを 2026-06-06 完了** (旧WP0.4) | ✅**2026-06-06 コア完了**（置き場所✅・v2 I/O✅／Firestore本形との完全同期はC3.xで継続） |

---

# B. 環境・インフラ構築

> 動かす土台。GCP本体は✅済。**B1.3（実態確認）は 2026-06-06 完了**（Vertex疎通OK・OAuth Secrets gap 残）。残りは CI/ホスティング/IaC（W1〜）。App Hostingの所有者連携ブロックは組織化決定で解消。詳細は `docs/infra/*.md`。
> **担当の考え方**: B1（Google Cloudコンソール）＝**鉄田**（GCPオーナー）／B3（GitHub・App Hosting連携・Cloud Build接続）＝**鉄田**（GitHub組織 `cloud-dojo` への移管・オーナー権限取得は✅2026-06-05完了・MTG 2026-06-05決定）。

## B1. GCP基盤・認証（IAM/OAuth/Secrets）← Google Cloud系＝鉄田

> **実装メモ（B1.3）**: まず実在確認（[p1-gcp-setup-runbook.md](../infra/p1-gcp-setup-runbook.md)）→無いものだけ作る。ADC＋`GOOGLE_GENAI_USE_VERTEXAI=TRUE`・`GOOGLE_CLOUD_PROJECT=publishr-498123`・`GOOGLE_CLOUD_REGION=asia-northeast1`。OAuth Secrets は Secret Manager か GitHub Secrets の住み分けを明記。台帳更新＝[gcp-setup-log.md](../infra/gcp-setup-log.md)。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| B1.1 | GCP IAM 2人招待・OAuth同意画面（3スコープ・テストユーザー） | Google Cloud上で2人がアクセスできるよう権限付与し、Googleログイン画面（Drive/Calendar/Tasksの利用許可を取る画面）を設定 | 鉄田 | W0（6/1–7） | A5.1 | デモ垢で3ソース承認可（GCP本体は✅済） (旧WP0.2) | ✅**2026-06-04完了**（IAM 2人・同意画面Production・テストユーザー・クライアント`Publishr Web`・GitHub Secrets計6本） |
| B1.3 | **GCP基盤の実態確認＋Vertex疎通** | 既存GCP資源の実在を突き合わせ、無いものだけ作る。ADC設定＋Vertex Gemini最小呼び出しでC1.0.1の足場を確認 | 鉄田 | W0（6/1–7） | B1.1 | [gcp-setup-log.md](../infra/gcp-setup-log.md)／[p1-gcp-setup-runbook.md](../infra/p1-gcp-setup-runbook.md) STEP A 実行。プロジェクト・API・Firestore・GCS・SA・Langfuse Secrets・**Vertex Gemini疎通スモーク成功** (旧—) | ✅**2026-06-06 完了**（gap＝OAuth Secrets未登録・予算アラート/Auth Googleプロバイダはコンソール確認残） |
| B1.2 | OAuth本番リダイレクトURI追記 | サーバー公開後、Googleログイン後の「戻り先URL」を本番用に1行追記する作業（`https://<backend URL>/api/auth/google/callback`） | 鉄田 | W2–W4（6/15–7/5） | backendデプロイ | 現状は仮 `http://localhost:8080/...` のみ。CLIENT_ID/SECRETは不変 (旧WP0.7) | 🔜backend待ち |

## B2. リポ・モノレポ・ローカル環境
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| B2.1 | GitHubリポ作成・モノレポscaffold | ソースコードを置くGitHub倉庫を作り、フォルダ構成（apps/agents/packages/eval/docs）を用意 | 一瀬 | W0–W1（6/1–14） | A5.1 | 2人がpush可・ディレクトリ確定（infra/TerraformはB4で投入） (旧WP0.3) | ✅リポ作成・collaborator・scaffold済（**2026-06-05：組織アカウント `cloud-dojo` へ移管完了→`cloud-dojo/publishr`・鉄田にオーナー権限付与済**） |
| B2.2 | ローカル環境統一（Python3.11/ADK SDK/Node） | 2人のPCで同じバージョンのツールを使うよう揃え、動作の食い違いを防ぐ | 鉄田・一瀬 | W1（6/8–14） | B2.1 | バージョン固定 (旧WP0.6) | 🟡**ローカルdev実行モード整備（2026-06-07）**＝`npm run dev:mock`（mock・認証なし）／`dev:emulator`＋`npm run emulators`（Firebase Auth/Firestoreエミュレータ・要Java＝OpenJDK 21導入済）・`firebase.json`にemulators・`firebase.ts`にconnect配線・手順書`docs/infra/local-sandbox.md`。**バージョン固定本体（Python/Node/ADK SDKの統一）は残** |

## B3. CI/CD・ホスティング（Actions/Cloud Build/App Hosting）← 鉄田がGitHub連携を実施（組織移管・オーナー権限完了）
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| B3.1 | CI/CD空パイプライン疎通 | コードをpushしたら自動でテスト→公開が動く「配線」を、まず中身カラ（"Hello"表示だけ）で通して土台を作る | 一瀬 | W1（6/8–14） | B2.1 | push→Actions→Cloud Run "Hello"（C1.0と兼用） (旧WP0.5) | 🔜着手前 |
| B3.2 | GitHub Actions → Cloud Build → Cloud Run 自動デプロイ（方式A=GitHub App直結） | mainブランチに反映したら自動でサーバー(Cloud Run)へ公開される仕組みを完成させる。**Cloud Build↔GitHub接続は方式A（GitHub App直結）で確定（G1-18・MTG 2026-06-05）＝鉄田はオーナー権限取得済（2026-06-05）→鉄田が接続** | 鉄田 | W4（6/29–7/5） | B3.1 | mainマージで自動デプロイ (旧WP6.1) | ✅**実装済（2026-06-11・PR#17・一瀬が代替経路で先行）**＝方式A(GitHub App直結・鉄田)の代わりに **GitHub Actions → Cloud Run（WIF keyless・鍵JSON無）**。`ci.yml` の deploy ジョブ＝`needs:verify`・main push/dispatch時のみ・`gcloud run deploy --source`(env/SA保持)。verify(eval-gate 7/8含む)通過が前提＝品質割れは未デプロイ。WIF=github-pool/provider(cloud-dojo組織限定)＋publishr-ci-deployer SA(cloud-dojo/publishrのみ借用)。IaC=`infra/terraform/cicd.tf`。**実機検証✅**＝mainマージで 00006→**00007-nsw** 自動デプロイ・env/SA保持・/api/healthz 200。**注: 現状は全main pushで再デプロイ(冪等)＝path filterは任意follow-up** |
| B3.3 | **Firebase App Hosting backend 作成（フロント本番ホスティング）** | フロント画面をネット公開する場所(App Hosting)を用意し、GitHubと連携して自動公開する。**組織移管（`cloud-dojo/publishr`）・鉄田オーナー権限は✅2026-06-05完了→鉄田が GitHub App 連携を実施** | 鉄田 | ~~W1~~→**W0** | A5.1 | `apps/web`をApp Hostingでmock公開（G1-7）。live=`main`／root=`apps/web`／region=`asia-east1`。backend作成＋GitHub App連携完了。**Turbopack+npm workspaces問題を解消**（root `workspaces`削除・shared-schemaベンダーコピー into `apps/web/src/lib/`）。build-010で成功。(旧WP0.8) | ✅**2026-06-06完了**（`publishr--publishr-498123.asia-east1.hosted.app` でmock公開中） |

## B4. IaC（Terraform）
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| B4.1 | Terraform IaC（Cloud Run/Scheduler/Pub-Sub/IAM/indexes） | クラウド設定を手作業でなくコードで管理し、誰でも同じ環境を再現できるようにする | 一瀬 | W4（6/29–7/5） | 各基盤 | コア資源をコード化 (旧WP6.4) | ✅**実装済（2026-06-10・PR#13・前倒し）**＝`infra/terraform/`（Cloud Run/Pub-Sub topic+push sub/Scheduler/SA×2/Artifact Registry/IAM×6＝16リソース）。imageは gcloud/CI 管理(`ignore_changes`)・URL自己参照はlocalsで回避・mock既定。README に既存環境の`terraform import`手順＋C4.9セキュリティ注記。**残＝`terraform validate/apply`を terraform入り環境/CIで（ローカル未インストール）／Firestore index は`firestore.indexes.json`(firebase)側のまま** |

---

# C. 実装

> コーディング本体。**C0 は 2026-06-06 完了**。**C1.0.1（H2 MiniLoop）は 2026-06-06 完了**。次のクリティカルパスは **C1.1–C1.6＋C3.x（モードA全STEP＋Firestore）**。STEP単位で内部分解する。

## C0. ローカル基盤固め

> **🧭 実態（2026-06-07）**: mock経路を常時緑に保ち、実LLM差し替えの継ぎ目（シーム）を敷設。**C0.1/C0.2 完了済み→C1.0.1 も完了→C1.1 へ進行可**。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C0.1 | **mock回帰復旧** | `make verify`＋`make eval`＋`make pipeline`＋`make smoke` を全緑に戻す。`eval/eval_set.yaml`（v2）と `scripts/eval_harness.py` の不整合を解消 | 鉄田 | W0（6/1–7） | — | pytest 60 passed, 1 skipped・Eval 8件PASS・pipeline却下→再提出証跡・smoke E2E (旧—) | ✅**2026-06-06 完了**／**2026-06-07 再緑化**（`91d3282`のペルソナ不整合でtest-py赤化→佐倉美咲へ全面再オーサリングで復旧・60 passed・`3e4b03b`・I-24。make smoke は本機=Windows OpenSSL/POSIX 環境問題で未実行） |
| C0.2 | **実装シーム敷設** | v2 I/O schema・state keys・prompt loader/registry/render・LLM provider・`PUBLISHR_LLM` dispatcher・dev/prod実行プロファイル・実LLMコストガードを追加。**mock時の挙動差分ゼロ**を維持 | 鉄田 | W0（6/1–7） | C0.1 | `packages/shared-schema/.../agent_io.py`・`agents/publishr_agents/prompts/*`・`llm/provider.py`・`pipeline.py` dispatcher・単体テスト緑 (旧—) | ✅**2026-06-06 完了** |

## C1. エージェント・モードA（自律企画）★

> Cloud Scheduler 週3回（月〜土の稼働日内・各回4冊）で起動し、観測→読者分析→企画→著者生成→編集→装丁を回して棚に4冊 draft で並べる。日曜日は通常入荷停止・セレンディピティ本1冊のみ生成。保持期間=過去4週間（最大約48冊）。**【2026-06-18 MTG変更: 旧「土/水=本命5冊、日=セレンディピティ5冊・週15冊」→新仕様】**
> **実装メモ（C1.1–C1.6）**: STEP2フル（`vertex/step2_planning.py`・調査サブ3体＋owner/leader Pro）／STEP1+STEP0（`ReaderAnalystAgent`＋`ObservationTool`・実Drive観測はC4）／STEP3+STEP4（`PersonaGeneratorAgent`＋`PreviewEditLoop×5`）／STEP5（`CoverParallel`・Imagenは`ENABLE_IMAGEN`フラグ）。`vertex/state_bridge.py` で `LeaderVerdict` 履歴→`RejectLogEntry`／`PipelineResult` に additive で `leader_verdicts` 追加（既存契約不変）。開発runは `dev` プロファイル（1〜2冊・短文・Imagen mock・編集1R）。**C1.0.1未達なら C1.1以降の本格実装へ進まない**。各STEPの内部タスクは共通パターン（①プロンプト結線 ②エージェント定義＋モデル割当＋I/Oスキーマ ③state配線 ④単体検証）。DoDは [agent-io-contract.md](../design/agent-io-contract.md) の各§を参照。担当は全て**一瀬**（ランタイム実装）。
>
> **🧭 実態（2026-06-07）**: **mock経路**＝`agents/publishr_agents` に canned 出力で疎通済み（`SequentialAgent`: observe→reader→`ParallelAgent`(企画3体)→選抜ゲート→著者アジェンダ→装丁／`InMemoryRunner`・`test_pipeline.py`あり）。**C0.2 で `PUBLISHR_LLM` dispatcher・prompt loader・v2 I/O schema の差し替え口は敷設済み**。**C1.0.1（H2）**＝`agents/publishr_agents/vertex/miniloop.py` で実Vertex MiniLoop（調査サブ1体＋owner/leader Loop＋escalate）を実証済み。**フルパイプラインは未**＝調査サブ×3(C1.3.1)・キャスティング5人2軸(C1.4)・プレビュー編集ループ(C1.5)・mock `build_pipeline` の選抜ゲート実escalate化はこれから。各STEPの「実装」は**実モデル＋v2 I/O＋実ループへの作り込みが本体**＝C1.1以降は原則 🔜（**C1.0.1ゲート通過済み→C1.1着手可**）。

### C1.0 ADK基盤・疎通(MiniLoop)

> **着手条件**: C0.2＋B1.3 通過済み。**✅2026-06-06 完了（H2）**。
> **実装メモ**: `LoopAgent(max_iter=3)` ＝ 調査サブ1(Flash+`google_search`) → owner1(Flash) → leader1(Pro) → `LoopBreakAgent`（custom BaseAgent）。leaderが `LeaderVerdict` を `output_key="leaderVerdict"` に出力 → `LoopBreakAgent` が `rejectionFeedback`/`approvedPlan` を state_delta へコピーし、`decision=="approve"` で `EventActions(escalate=True)`。round3は belt-and-suspenders（プロンプト帯＋コード帯で強制採用）。**利用クラウド＝Vertex Gemini＋Langfuseのみ**（Cloud Run/Firestore/Pub/Sub/Schedulerはまだ入れない）。再現性成果物＝`scripts/run_miniloop.py`・`observability.trace_miniloop`（Langfuse SDK直）・`@pytest.mark.vertex` 最小テスト（`PUBLISHR_RUN_VERTEX=1` で live 実行）。固定success JSONファイルのコミットは任意残。3日詰まったら C1.3 のみ LangGraph（**H2通過のため現時点では不要**）。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.0.1 | ★**ADK疎通(MiniLoop)** | **ADK=GoogleのAIエージェント開発キット**。「疎通」＝最小構成で実Vertex動作し、score<閾値で再ループ→score≥閾値で`escalate`脱出を実証する**最重要技術検証** | 一瀬 | **W0–W1（6/1–14）** | C0.2,B1.3 | ①grounding実ソース取得 ②ownerがsub読む ③leaderがscore付verdict ④score<閾値で再ループ（rejectionFeedback反映）⑤score≥閾値でescalate脱出 ⑥round3強制採用。Langfuseに反復→脱出。再実行CLI・vertex最小テスト（ADK §7・**C1.0.1ゲート**） (旧WP1.1★・M1) | ✅**2026-06-06 完了**（H2実証・commit `edb6611`・`vertex/miniloop.py`＋`run_miniloop.py`＋`test_miniloop_vertex.py`） |

### C1.1 STEP0 観測
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.1.1 | 観測ツール実装（Drive/Calendar/Tasks ±14日） | ユーザーのDrive・カレンダー・ToDoを前後14日分読み取り、AIが状況把握する材料（生データ）を集めるツール | 一瀬 | W2（6/15–21） | B1.1,C1.0.1 | ObservationBundle生成（§2） (旧WP1.2) | 🟡**実装済・live検証残（2026-06-07）**＝`agents/publishr_agents/observe/`（transform純粋ロジック＋`FixtureObservationSource`＝既定オフライン決定的＋`GoogleObservationSource`＝実API隔離・`PUBLISHR_OBSERVE`で切替）。型付き`ObservationBundle`（§2）＋`ConnectedSources`をschemaに追加（py/ts）。CLI`scripts/run_observe.py`・`@pytest.mark.google`最小テスト。±14日窓/4000字トリム/Tasks未完了+直近完了をtransformに一元化。**残＝OAuth同意→実Drive/Calendar/Tasks取得のlive検証（鉄田のOAuth/Picker=C4.1と接続）** |
| C1.1.2 | Drive Pickerサーバ側連携 | Driveは全ファイルを見られない仕様のため、ユーザーが選んだフォルダだけ取得する画面連携をサーバー側で実装 | 一瀬 | W2（6/15–21） | C1.1.1 | 選択フォルダのみ取得＝`connectedSources.drive.folderIds[]` で保持（G1-13＝フォルダ単位・Google Picker前提で確定・MTG 2026-06-05） | 🟡**サーバ側読取実装済（2026-06-07）**＝`connectedSources.drive.folderIds[]` を `User` schemaに追加し、fixture/google 両ソースで folderId 配下のみにスコープ（offline test で folderId スコープを検証）。`scripts/google_oauth_bootstrap.py` で OAuth トークン取得。**残＝Picker UI（C4.1=鉄田）からの folderIds 書込と疎通** |

### C1.2 STEP1 読者分析
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.2.1 | STEP1 読者分析エージェント（Pro・3層Profile）＋state配線 | 集めた材料から、ユーザー像を3層（①基本属性 ②今の仕事の状況 ③読書傾向）で分析するAIを実装 | 一瀬 | W2（6/15–21） | C1.1.1 | ReaderProfile{base/currentWork/readingBehavior}保存（§3） (旧WP1.3) | ✅**実装・実Vertex live実証済（2026-06-07）**＝`agents/publishr_agents/reader/`（`deterministic.py`＝既定オフライン・bundle→3層Profile抽出／`vertex_agent.py`＝実Gemini Pro LlmAgent・`output_schema=ReaderProfile3Layer`・miniloopパターン／`__init__`=PUBLISHR_LLM dispatch）。step1_reader_analystプロンプト・registry・model_for(Pro)既設を結線。CLI`scripts/run_reader.py`（STEP0→STEP1縦串）。test_reader（決定的10件）＋`@pytest.mark.vertex` gated。**live実証**＝fixture観測→実Pro→3層Profile（challenges/evidenceが観測の固有名に紐づく・佐藤健一/競合A社/田中健太まで踏込）。`users/{uid}.profile`永続化はC3/BFF結線時。残＝STEP2(C1.3)への結線 |

### C1.3 STEP2 企画3階層（★必然性の本丸）
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.3.1 | 調査サブ×3（Flash＋Google検索grounding） | 3体のAIが手分けして「①読者の状況 ②市場・競合(Google検索) ③テーマ知見(Google検索)」を調査。AIが外部の実データを取りに行く部分 | 一瀬 | W2（6/15–21） | C1.0.1,C1.2.1 | subReaderContext/subMarket/subThemeInsight 生成・取得URL記録（§4） (旧WP1.4) | ✅**実装・live実証（2026-06-07）**＝`agents/publishr_agents/planning/vertex_agent.py` の `ParallelAgent[sub_reader_context(schema)/sub_market(google_search)/sub_theme_insight(google_search)]`。A=内部・B/C=grounding（text出力＝miniloop実証構成）。live で実Google検索の market 調査を確認 |
| C1.3.2 | 企画担当者（Pro・8項目フレーム立案） | 調査結果をもとに、本の企画書（タイトル/読者状況/差別化など8項目）を立てるAI | 一瀬 | W2（6/15–21） | C1.3.1 | PlanProposal 8項目（§4） (旧WP1.4) | ✅**実装・live実証**＝`_plan_owner`(Pro・output_schema=PlanProposal)。live で観測grounded な8項目企画（実名「佐藤さん」・6/5役員報告・marketGap反映の差別化）を生成 |
| C1.3.3 | 企画リーダー（Pro・4観点採点・閾値70・最高3R差し戻し） | 企画書を4観点で採点し、70点未満なら「やり直し」を指示するAI（最大3回）。**AIである必然性を見せる核** | 一瀬 | W2（6/15–21） | C1.3.2 | score/round/rejectionFeedback記録・escalate（§4） (旧WP1.4) | ✅**実装・live実証**＝`_plan_leader`(Pro・LeaderVerdict)＋miniloop `LoopBreakAgent` 再利用。**live: threshold101→R1 revise(98)→R2 approve(102)＝差し戻し理由「失敗談で差別化を」をR2が実反映**＝必然性の核を実証。決定的オフライン path も `deterministic.py`(reject→approve trace・既定)。dispatcher=PUBLISHR_LLM・CLI`run_planning.py`(STEP0→1→2縦串)・test_planning(決定的12件)＋gated |

### C1.4 STEP3 キャスティング
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.4.1 | キャスティング編集者（架空著者5人・voiceStyle×format 2軸） | テーマに合う「架空の著者」5人を、文体×文章形式の2軸で毎回生成するAI（お気に入り著者を15%混ぜる） | 一瀬 | W2–W3（6/15–28） | C1.3.3 | GeneratedPersonaSet 5人（§5-3a） (旧WP1.5) | ✅**実装・live実証（2026-06-07）**＝`agents/publishr_agents/casting/`（`deterministic.py`＝5人2軸分散・favorite1枠／`vertex_agent.py`＝persona_generator Pro・output_schema=GeneratedPersonaSet／`__init__`=PUBLISHR_LLM dispatch）。step3プロンプト結線・CLI`run_casting.py`(STEP0→1→2→3縦串)・test_casting(決定的9件)＋gated。live: 実Proで5著者を2軸分散生成。code-review Approve（favorite注入の2軸保持を修正） |

### C1.5 STEP4 プレビュー編集
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.5.1 | プレビュー編集ループ（編集長⇄著者5人・1R・3観点） | 著者AI5人が各自プレビュー（7項目）を書き、編集長AIが採点して1回だけ直す。棚に5冊 draft で並べる | 一瀬 | W3（6/22–28） | C1.4.1 | BookDraft 7項目×5冊 draft保存（§5-2） (旧WP1.6) | ✅**実装・live実証（2026-06-07）**＝`agents/publishr_agents/preview/`（`deterministic.py`＝5冊BookDraft+1R実演／`vertex_agent.py`＝author_preview/editor_preview Pro を Pythonで著者→編集長→1R改稿ループ・`limit`でコスト制御／`__init__`=PUBLISHR_LLM dispatch）。CLI`run_preview.py`（**STEP0→1→2→3→4 フル縦串**・段階別LLM切替）。live: STEP4を実Proで2冊（観測grounded・ペルソナで作風差別化・editor approve）。`make verify` pytest 127 passed,6 skipped・typecheck緑。code-review Approve（MEDIUM 1点反映）。Firestore永続化(book_id/ownerUid付与)はC3/BFF結線時 |

### C1.6 STEP5 装丁
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.6.1 | 装丁（Imagen・dev時モック） | Imagen（画像生成AI）で表紙画像を作る。開発中はコスト節約のためダミー画像で代用 | 一瀬 | W3（6/22–28） | C1.5.1 | coverUrl付与（§6・ENABLE_IMAGEN） (旧WP1.7) | ✅**実装・実Imagen live実証（2026-06-07）**＝`agents/publishr_agents/cover/`（`deterministic.py`＝coverVariant(CSS b1..b10)＋canned coverPrompt・coverUrl=None／`vertex_agent.py`＝Flash coverPrompt／`imagen.py`＝google.genai実Imagen(imagen-3.0・PUBLISHR_IMAGEN_LOCATION既定us-central1)→PNG保存→coverUrl／`__init__`=PUBLISHR_LLM＋ENABLE_IMAGEN dispatch）。CLI`run_mode_a.py`（**STEP0→5 モードA完全縦串**）。live: ENABLE_IMAGEN=1 で実表紙2枚生成（896×1280・3:4・文字焼かず装画のみ・著者軸で作風差別化）。`make verify` pytest 136 passed,7 skipped・typecheck緑。code-review Approve。Firestore/GCS本保存はC3.3 |

### C1.7 自律トリガー(Scheduler)
| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C1.7.1 | Cloud Scheduler 曜日別トリガー（土/水/日） | 毎週決まった曜日に自動で企画が走る仕組み（Cloud Scheduler）。デモでは手動起動も可 | 一瀬 | W3（6/22–28） | C1.3.3 | 自律起動で棚更新 (旧WP1.8) | ✅**本番デプロイ済（2026-06-10）**＝Cloud Scheduler `publishr-honmei`（`0 6 * * 3,6`・Asia/Tokyo・OIDC=publishr-pubsub-push SA・audience=trigger URL）→ `POST /api/trigger/planning` → モードA(mock)→佐倉(5JLL)Firestore自律入荷。手動実行(`gcloud scheduler jobs run publishr-honmei`)で arr_p* 即更新（created更新）を実機確認＝**Scheduler→Cloud Run→自律入荷が本番成立**。IaC正本化はB4.1(`infra/terraform`)。ローカル/mock版（`scheduler.py`曜日→themeKind純粋判定＋`run_scheduler.py --once/--watch`・test_scheduler 7件）も維持。**残（小）＝serendipity(日)差別化＝trigger に themeKind param 追加＋日曜ジョブ（cron `0 6 * * 0`・TF/docにコメント用意済）。「棚更新」のFirestore永続化は入荷upsertで達成済** |

## C2. エージェント・モードB（後追い執筆）

> **実装メモ（段階導入）**: 手動1冊（`mode_b/` BodyEditLoop・`scripts/run_body_once.py`・本文3〜5p・1R）→ 予約API接続(C2.1) → Pub/Sub worker(C2.2) → Scheduler自律(C1.7)。**大型生成物をstateに溜めない**（章本文はGCS・stateはref+summaryのみ）。同時5冊transactionはC2.2で入れる。
>
> **🧭 実態（2026-06-05）**: 予約フローの **mock が `apps/api` にある**（`reservation_service.reserve_now`＝`draft→reserved` の単純status遷移＋`ConflictError`／`advance`＝`reserved→writing→published` をタイマーで進める疑似ワーカー）。**ただし①同時5冊の Firestore transaction(I-20)・②Pub/Sub 実ワーカー・③本文編集ループ(編集長⇄著者・最高3R) は未**。C2.1 は mock 済み／C2.2・C2.3 は未着手。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C2.1 | 予約API `POST /reserve`（同時5冊チェック＋Pub/Sub発行） | ユーザーが本を「予約」したら執筆を始める窓口。同時に5冊までの制限を入れる | 一瀬 | ~~W3~~→**W1完了** | C3.1 | API契約 §3・I-16／予約の原子性＝Firestore transaction で count確認→条件付き遷移（I-20） (旧WP2.1) | ✅**2026-06-09・PR#7**（同時最大5冊ガード＝reserved+writing<cap・満杯はConflictError(409)・`config.max_concurrent_reservations=5`）。**残＝並行原子性 Firestore transaction(I-20) はハードニングで未** |
| C2.2 | Pub/Sub → 執筆ワーカー起動 | 予約を受けて、裏側で執筆処理を起動する仕組み（メッセージ連携）。二重起動を防ぐ | 一瀬 | ~~W3~~→**W1完了** | C2.1 | 冪等ガード（I-20） (旧WP2.2) | ✅**2026-06-09・PR#8・live検証済**（`QUEUE=mock\|pubsub` シーム・`write_queue`／冪等worker `process_write_job`／`pubsub_queue`＋`/api/worker/write`(push OIDC検証)。実Cloud Pub/Sub: topic `publishr-writing`・push sub・SA `publishr-pubsub-push`・予約→publish→push→worker→published を実機確認） |
| C2.3 | 本文編集ループ（編集長⇄著者・最高3R・約100p） | 著者AIが約100ページ書き、編集長AIが採点→弱い章だけ書き直す（最大3回）。完成したら本文を保存 | 一瀬 | ~~W3~~→**W1完了** | C1.5.1,C2.2 | published・editRounds記録（§7） (旧WP2.3) | ✅**2026-06-09・PR#6/#9**（モードB `mode_b/`＝編集長⇄著者・**最高3R**・弱章のみ改稿。worker の本文生成を write_body→mode_b に差替・editRounds を `Book.edit_round` 記録。**残＝約100p化＋GCS本文保存(C3.3)・mode_b vertex live は別軸**） |

## C3. データ/状態基盤（Firestore/GCS）

> **実装メモ（C3.1/C3.4/C3.5）**: `RepositoryProtocol` に Firestore実装追加。`firestore-security-rules.md`/`firestore.indexes.json` デプロイ。`DATA_SOURCE=firestore` で plans/books/personas/observations 保存。`ownerUid` 規約。クライアント直書き可は `initialProfile`/`highlights`/`feedback`/`favoriteAuthors` 等に限定。rules unit/emulator test 追加。FastAPIに Firebase Admin SDK 共通依存（`/healthz` 以外は Bearer 検証・bodyの `userId` は信用しない）。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C3.1 | Firestoreスキーマ＋セキュリティルール デプロイ | 設計したデータベースの保存形式とアクセスルールを、実際にクラウドへ反映する（設計はA2.5） | **鉄田** | W0（6/1–7）→**6/6完了** | B1.1 | ルール本文デプロイ（読書ログfeedback集約I-9・観測束ObservationBundleのmatch追加I-19＝MTG 2026-06-05で確定済を反映） (旧WP3.1) | ✅**2026-06-06完了**（firebase.json・.firebaserc・firestore.rules・firestore.indexes.json 生成→`firebase deploy --only firestore:rules` 本番デプロイ済み）／**2026-06-07：`users/{uid}` update を『本人なら initialProfile/favoriteAuthors 変更可』に緩和し再デプロイ**（旧「initialProfileは初回のみ」制約が登録・プロフィール編集を黙ってpermission denied化していた・I-6） |
| C3.2 | 複合インデックス列挙＋firestore.indexes.json | 一覧画面の検索が速く正しく動くよう、DBに索引を登録する（無いと実行時エラーになる） | **鉄田** | W2–W3（6/15–28） | C4.2,C4.7 | 実行時エラー回避（I-15） (旧WP3.2) | 🔜着手前（C4のクエリが固まり次第追記・firestore.indexes.json骨格は✅） |
| C3.3 | GCS本文保護（署名付きURL or IAM） | 本文ファイルを他人が読めないよう、アクセス制限をかける | **鉄田** | W3（6/22–28） | C2.3 | 他者本文を読めない（I-10） (旧WP3.3) | 🔜着手前 |
| C3.4 | 観測ログ保存先コレクション（`users/{uid}/observations/{YYYY-MM-DD}`） | STEP0で集めた観測データを保存する場所（コレクション）を用意する | **鉄田** | W0（6/6完了・C3.1に内包） | C1.1.1 | STEP0が書込可＝`users/{uid}/observations/{YYYY-MM-DD}` サブコレクション（日付docID＝冪等・フル束インライン・サーバ書込/本人read／I-19＝MTG 2026-06-05で確定） (旧WP3.4) | ✅完了（C3.1に内包）firestore.rules の `match /users/{uid}/observations/{date}` で owner読み・書込み=false（サーバ専用）を宣言済み |
| C3.5 | **BFF（apps/api）の Firestore リポジトリ実装＋mock→firestore切替** | `apps/api` は `protocol.py`＋`mock_repository.py` のリポジトリパターンで実装済み。`RepositoryProtocol` の Firestore 実装を足し、mock から切替える（＝抜け漏れ補完・2026-06-05起票） | **鉄田** | W0（6/6完了） | C3.1 | Firestore実装を追加し `DATA_SOURCE=firestore` で起動可（フロントC4.9・モードB C2.x の本接続前提）。mock側✅ | ✅**2026-06-06完了**（`firestore_repository.py` 実装・`firebase-admin>=6.5` 追加・`deps.py`でDATA_SOURCE切替・`uv run python -m pytest` 11件グリーン） |

## C4. フロント（書店UI・16ルート）

> **実装メモ（E2E・M2★）**: C4.9=Firebase Auth＋Firestore直購読/直書き・`NEXT_PUBLIC_DATA_SOURCE=firestore`。C4.1/C1.1.2=OAuth start/callback＋Drive Picker（OAuth間に合わなければfixture観測で縦通し優先）。手動トリガー `POST /api/trigger/planning`（許可uid・レート制限・実行中ロック）。C4.8=`map/` が `leader_verdicts` の却下→採用を描画＝**基準1の画**。最小Cloud Run疎通（APIのみ・本番完成ではない）。

> **🧭 実態（2026-06-07更新）**: `apps/web`(Next.js) に **C4.2–C4.8 はUI code-complete（16ルートビルド緑・mock動作確認済）**。Firebase Auth＋Firestoreプロバイダも実装済（mock時は休眠）。**C4.1はUIシェルのみ**＝initialProfile登録画面はあるが、**Google Drive/Calendar/Tasks の実連携ページ（OAuth接続・Drive Picker実機能）は未設計・未実装**。
> **残作業**: **Google連携ページ実装（C4.1）＝機能設計から要対応**（C4.9は✅2026-06-07完了済み）。担当は基本**鉄田**。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C4.1 | 登録フォーム＋OAuth接続＋Drive Picker UI | ユーザー登録画面・Googleログイン・Driveファイル選択UIを作る | 一瀬 | W2（6/15–21） | A5.2,C1.1.1 | initialProfile直書き・3ソース接続（G1-13） (旧WP4.1) | 🟡**initialProfile登録フローは実装/整備済み・OAuth/Drive Picker部分のみ🔴未**。**【2026-06-07完了分】** 登録ボタンの固まり解消（`saveInitialProfile`のlocalStorageキャッシュ＋Firestore非throw化・`persist`のtry/catch化）・登録後トップ`/`へ直接遷移・アカウント即反映・初期設定に「新しい出会いの幅」追加・ログイン時に初期設定済みならオンボーディングをスキップ（`hasCompletedOnboarding`）・初回体験「空→生成中→15冊」(mock)。**残る🔴＝Google Drive/Calendar/Tasks の実連携機能のみ**＝OAuth接続フロー・Drive Picker実動作・接続状態表示は未着手（データ連携トグルはlocalStorageのデモ実装・Firestore connectedSourcesはサーバ書込前提でクライアント未対応）。機能設計（Picker UI仕様・接続状態の保存先）から要対応。C1.1.1〔観測ツール〕・C1.1.2〔Drive Pickerサーバ側〕との接続設計も要整合。**【2026-06-09 コード再確認＝依然🔴未】**: `apps/web/src/app/(auth)/connect/page.tsx` は **モックトグルのみ**（`onConnect` は `isFirebaseConfigured` 時に `GET /api/auth/google/start`→authUrl遷移 を試みる設計だが **BFFにそのendpointは無い**ため localStorage フラグに縮退）。**Drive Picker 未実装**（`google.picker`/`gapi`/`developerKey` 痕跡ゼロ）。**BFFに OAuth endpoint 無し**（`/api/auth/google/start`・`/callback`）。※観測用Google OAuthは**CLI(`scripts/google_oauth_bootstrap.py`・task#7 L1=calendar+tasks)では実動**するが、UIボタン→実OAuth(L2)とは別物で未着手。本番化は C4前ゲート（state/IDトークン検証/許可uid/レート制限）込みで対応。**【2026-06-12 一瀬側バックエンド完成＝接続設計の本体】** BFF `routers/auth.py` に `GET /api/auth/google/start`（Firebase uid→HMAC署名state付き authUrl）・`GET /api/auth/google/callback`（state検証→code交換→token保存→connectedSources.enabled更新→`{webApp}/connect?connected=1`へ302）・`POST /api/connect/drive-folders`（Picker folderIds サーバ書込）を実装。`oauth_service`（state署名/検証・URL組立は決定的単体テスト・code交換は実Google隔離）／`token_store`（file既定＋Secret Manager本番・G1-5）／`config` OAuth項目／`upsert_user`。**【2026-06-12 Drive Picker UI もフロント実装＝C4.1 code-complete】** `apps/web/src/lib/googlePicker.ts`（GIS access token→`google.picker` フォルダ選択→`POST /api/connect/drive-folders`）・`(auth)/connect/page.tsx` 統合（`isPickerConfigured` 時のみ表示・選択フォルダchip）・型 `src/types/google-picker.d.ts`・`config.ts` に `NEXT_PUBLIC_GOOGLE_CLIENT_ID/API_KEY/APP_ID`。typecheck/lint 緑。**残＝GCPで Picker API 有効化＋OAuth Webクライアント/APIキー発行＋`apphosting.yaml` 投入＋ブラウザ実機QA**（コードは揃・contract＝`api-contract.md §4`） |
| C4.2 | 書店トップ（入荷一覧・入荷理由） | 入荷した本が並ぶトップ画面と「なぜこの本が入荷したか」の理由表示 | 鉄田 | W2（6/15–21） | C3.1 | draft本＋入荷理由表示 (旧WP4.2) | ✅**UI code-complete**（Firestore接続はC4.9） |
| C4.3 | 本詳細（BookDraft 7項目） | 本の詳細（タイトル/サブ/今あなたは/課題/核心/アジェンダ/序文）を見る画面 | 鉄田 | W2–W3（6/15–28） | C3.1,C1.5.1 | 7項目表示 (旧WP4.3) | ✅**UI code-complete**（Firestore接続はC4.9） |
| C4.4 | 著者選択・予約UI（同時5冊ガード） | 著者を選んで本を予約する画面（同時5冊の上限を表示） | 鉄田 | W3（6/22–28） | C2.1 | reserve呼び出し・上限表示 (旧WP4.4) | ✅**UI code-complete**（mock reserve タイマー動作確認済。Firestore接続はC4.9） |
| C4.5 | 読書画面・ハイライト・簡易FB | 本を読む画面と、ハイライト・読了/評価の保存（Firestore直書き） | 鉄田 | W3（6/22–28） | C3.1 | ハイライト保存・FB記録 (旧WP4.5) | ✅**完了**（KindleライクなUIに強化＝ドラッグ範囲ハイライト・3色選択ポップアップ・`startOffset/endOffset`文字単位記録。目次(`/contents`)・ハイライト一覧(`/highlights`)サブページ新設＋`?pi/?ch`ジャンプ機能） |
| C4.6 | お気に入り著者保存 | 気に入った著者を保存する機能（次回企画に15%混ざる） | 鉄田 | W3（6/22–28） | C3.1 | arrayUnion保存 (旧WP4.6) | ✅**UI code-complete**（読了ページのお気に入りボタン＋favoriteAuthor通知連動済。Firestore接続はC4.9） |
| C4.7 | わたしの書庫・通知バナー | 自分の本棚と、入荷/執筆完了のお知らせバナー（Firestore購読） | 鉄田 | W4（6/29–7/5） | C4.2 | 購読バナー（G1-15） (旧WP4.7) | ✅**UI code-complete**（サイドバー「最近読んだ本」・published本のみ最大5件・書庫表紙CSS強化。通知はNotificationBell実装済。Firestore購読接続はC4.9） |
| C4.8 | **ローカルUI仕上げ（レイアウト/行ずれ修正・全画面QA）** | 画面のレイアウト崩れ・行ずれ・モックとの差分を実機で確認して直す。修正量が多めで**デプロイ前の山場** | 鉄田 | W2–W4（6/15–7/5） | C4.1-C4.7 | `npm run dev:web`で全画面確認・修正 (旧WP4.8) | ✅**2026-06-07 完了**（**2026-06-06実施分**: 読書ページサブページ分離・ジャンプ機能・BookToc共有コンポーネント・本の概要ページ整理・目次章番号折り返し修正・サイドバー最近読んだ本・書庫表紙CSS強化。**2026-06-07実施分**: ①フィードバックチップ条件付きレンダリング修正（ページロード時に非表示・いいね/いまいちタップで展開）②`.rail-tools`の`position:sticky`削除でナビカードのジャンプ解消③ベルアイコン(🔔)＋通知ドロップダウンパネル新設（`NotificationBell.tsx`）＝入荷/執筆完了/お気に入り作家の3種・未読バッジ・全既読ボタン・各通知から`/books/{bookId}`概要ページへリンク④`AppNotification`型・`pushNotification`/`markNotificationRead`/`markAllNotificationsRead`等をBaseProviderに実装⑤MockProviderにseedNotifications（3件・決定的シード）＋reserve完了時自動通知⑥`useNotifications()`・`notifyFavoriteAuthor()`フック⑦読了ページの「お気に入り登録」でfavoriteAuthor通知生成。**Firestore本接続後の全画面QAのみ残**（C4.9依存）） |
| C4.9 | **Firestore本接続・Firebase Auth起動（mock→firestore切替）** | mockデータから本物のDB(Firestore)接続へ切替える。一瀬から設定値を受領後に作業 | 鉄田・一瀬 | W2–W3（6/15–28） | C3.1,B3.3,C2.1 | 一瀬から①Firebase設定値(`NEXT_PUBLIC_FIREBASE_*`)②~~ルールのデプロイ→✅C3.1完了済み~~③API3本URL・CORS④`ownerUid`規約 を受領後、`NEXT_PUBLIC_DATA_SOURCE=firestore`へ切替 (旧WP4.9) | ✅**2026-06-07 完了**（別セッションにて実施。`NEXT_PUBLIC_DATA_SOURCE=firestore`・Firebase Auth起動・Firestore読み書き接続完了） |

## C5. 品質・評価・観測・運用

> **実装メモ**: C5.3=自作 `eval_harness.py`（mock床）は残し、GEAP（`vertexai.evaluation`・region=`us-central1`）を併設。C5.6=2ループ＋grounding URL可視化。B3.2=lint→Eval Gate→Cloud Build→Cloud Run（方式A=GitHub App直結・鉄田）。B3.1で最小CI雛形を先に置く。

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C5.1 | W1 各プロンプト実テスト→調整 | 実際にAIへ指示文を流し、想定どおり出るか・悪い例を弾くかを確認して調整 | 鉄田・一瀬 | W1–W2（6/8–21） | C1.0.1 | Langfuseで出力確認 (旧WP5.3) | 🟡MiniLoopで research_subs/plan_owner/plan_leader の実Vertex確認済（C1.0.1）／全11本の網羅は未 |
| C5.2 | 良い/悪い例を eval fixture に兼用反映 | 良い例/悪い例を、AIの手本（few-shot）とテストの両方に使い回す | 鉄田 | W2（6/15–21） | C5.1,A4.1 | few-shot＋Eval両用 (旧WP5.4) | 🟡**兼用構造done（決定的・2026-06-07）**＝採点系4本(leader/editor×2/judge)の✅良い例/❌悪い例を `loader.py` が単一ソースから抽出→`eval_harness.check_fewshot_eval_alignment()` が「良い例=合格・悪い例=不合格・judge=eval_set帯と整合」を実LLM無しで回帰（test 2件追加グリーン）。残＝**実judge(LLM)実行での検証はC5.4/C1.0疎通待ち** |
| C5.3 | **Eval judgeゲート**をCIに組込 | AI品質が基準(70点)未満なら自動でデプロイを止める品質ゲートをCIに組み込む | 一瀬 | W4（6/29–7/5） | C5.x,**I-21** | failでデプロイ停止（MVP §9）。`eval/eval_set.yaml` を LLM-judge で採点・`cases`=ゲート(8件中7)/`borderlineCases`=診断で読む（I-21）。**mock用 `scripts/eval_harness.py` は v2 整合済み（C0.1✅）**。CI本番ゲート＝Vertex AI Gen AI Evaluation Service（GEAP）を B3.2 と併設 (旧WP6.2) | ✅**実装済（2026-06-10・PR#15）**＝`scripts/eval_gate.py`＝cases(8)をjudge採点→expectedBand内なら正答→ceil(87.5%)=**7/8で通過・未満は exit 1**（基準割れでデプロイ停止）。borderline(2)は診断専用でゲート外(I-21)。mock judge(4観点×0-25・決定的・$0・教養越境は中レンジclamp)で**8/8正答を実測**。`make eval-gate`＋**`.github/workflows/ci.yml`**(B3.1: setup→verify→eval→eval-gate・CI実機green)。test_eval_gate 7件。**残＝vertex判定(GEAP本番ゲート・B3.2併設・課金)はoffline未配線(NotImplemented)** |
| C5.4 | judge再現性テスト（複数回採点・標準偏差確認） | 採点AIが毎回ブレない（同じ点を出す）か複数回試して信頼度を確認 | 一瀬 | W2–W3（6/15–28） | C5.1,**I-21** | ゲート判定の信頼度確認（v2 Evalハーネス=I-21 が前提。境界ケース `eval_b1/b2` で閾値70近傍の判別を測る） (旧WP7.2) | 🟡**一瀬ハーネス実装済・実judge運用残（2026-06-12）**＝`scripts/eval_reproducibility.py`（`make eval-repro`）＝cases8＋borderline2を N回採点し mean/σ/CV と**判定の自己一致率**（≠正答性＝C5.3の担当）を出す。`--max-cv`/`--min-stability` で逸脱は exit 1。**再現性=採点のブレを測る指標**として整理（mockは決定的＝σ=0・一致100%＝床、実ブレは `--backend vertex`＝gated/課金）。test 4件。**所見**: mock は eval_b1 を100点（[68,80]外）と再現的に採点＝境界帯の較正は実judge前提（mockは判定の向き=70との上下のみ正しい）。**【2026-06-12 実judge配線済（gated）】** `eval_gate.judge_plan(backend="vertex")`＝実 Gemini Pro（`eval_judge.md`ルーブリック・readerProfile＋plan→4観点JSON→mock互換dict・`PUBLISHR_JUDGE_TEMPERATURE`で振れる）。`@pytest.mark.vertex`の最小liveテスト（`test_eval_gate_vertex.py`・既定skip）。**残＝`PUBLISHR_RUN_VERTEX=1 PUBLISHR_EVAL_BACKEND=vertex make eval-repro` で実σ/CV測定（課金・ADC要）** |
| C5.5 | 閾値・ルーブリックの運用調整 | 合格ライン(70点等)や採点基準を、実データを見ながら微調整 | 一瀬 | W4（6/29–7/5） | C5.4 | 実データで微調整（I-1/I-18） (旧WP7.3) | 🟡**一瀬の調整土台実装済・実データ微調整残（2026-06-12）**＝`scripts/eval_threshold_sweep.py`（`make eval-sweep`）＝本命合格ライン `honmeiMin`（`eval_set.yaml` `meta.threshold`＝単一調整箇所）を±10で振り、高関連の通過数と境界 `eval_b1`(ギリ通す)/`eval_b2`(ギリ落とす)の合否を一望。test 4件。**所見（mock決定的）**: 70は **60–75 まで本命4/4通過＋境界ペア正しく分離（b1通過/b2落下）の余裕帯**、80で本命1件取りこぼし。**【2026-06-12 実judge配線済（gated・C5.4と同じ）】** sweep/repro は `--backend vertex` で実Gemini採点に切替可。**残＝実judgeスコアでの最終閾値微調整・ルーブリック文言調整（`PUBLISHR_RUN_VERTEX=1`・課金・実データ）** |
| C5.6 | Langfuse計装（2ループ＋grounding取得URL） | AIの動き（やり直しループ・検索URL）を記録・可視化し、AIの必然性を見せられるようにする | 一瀬 | W4（6/29–7/5） | C1.3.3,C1.5.1,C2.3 | 必然性の証跡が可視化 (旧WP6.3) | ✅**実装済（2026-06-10・PR#15）**＝`observability.trace_pipeline`＝企画リーダー差し戻し(対立①)・編集長本文(対立②)の**2ループ＋grounding URL**を1トレースで可視化（部分payload可・キー無/未導入はno-op・$0）。`grounding_urls_from_events`でADKイベントから検索URL(web.uri)抽出。`run_body_once`に編集ループ計装結線。MiniLoop用`trace_miniloop`も維持。test_observability 5件。**残＝実Langfuseキーでのlive送信確認（best-effort・任意）** |
| C5.7 | dev/prodフラグ運用 | 開発中は安く（ページ少・画像ダミー・冊数少）、本番だけフル、を切替える設定の運用 | 鉄田・一瀬 | W1〜（6/8〜） | B2.2 | dev既定で反復、本番のみprod (旧WP9.1) | 🔜着手前 |
| C5.8 | コスト実測→コスト概算.md上書き | 実際のAI利用料を測り、予算1万円で足りるか確認して概算書を更新 | 鉄田・一瀬 | W1（6/8–14） | C1.0.1 | 予算¥10,000耐性確認 (旧WP9.2) | 🟡MiniLoop初回実測あり（C1.0.1）／フルパイプライン実測は未 |
| C5.9 | エラー/リトライ/冪等/タイムアウト方針 | 失敗時の再試行・二重実行防止・時間切れの最小ルールを決めて実装 | 一瀬 | W1–W3（6/8–28） | C1.x,C2.x | 最小方針を決め実装（I-20） (旧WP9.3) | ✅**実装済（2026-06-10・PR#15）**＝`llm/resilience.py`＝transient分類・指数バックオフ(決定的)・`RetryPolicy`(env駆動)・timeout(asyncio.wait_for)・sync/async retry。方針はdocstringで明文化。非transient(スキーマ違反/CostGuard等)は即時送出＝無駄な再試行と課金回避。`mode_b/vertex_agent`の_run_text/_run_verdictをラップ(mock不変)。冪等性(I-20)は`process_write_job`既存(二重配信no-op・test_write_worker網羅)。test_resilience 12件 |

## C6. デモ・提出物

> **実装メモ**: デモデータ＝seed投入（佐倉美咲・部下7名）で録画再現性。必然性3証跡（却下→再提出を画に）必須。C6.7=実フロントスクショ5枚差替。7/10厳守。（公開クリーンリポ／図マスク版＝旧C6.8は2026-06-11にWBS外へ切り出し・別途作成）

| ID | タスク | タスク詳細（何をやる？） | 担当 | 予定週 | 依存 | DoD | 状態 |
|---|---|---|---|---|---|---|---|
| C6.1 | デモ動画台本（必然性3証跡を画に） | 審査用2.5分＋ピッチ内60秒の動画台本を作る。台本は完成、残りは録画 | 鉄田 | W1–W4（6/8–7/5） | — | 動画2本立て：①紹介2.5分／②デモ60秒。台本✅（`publishr_other/demo/動画台本/`）。**MTG 2026-06-05：①プロダクト紹介2.5分（ProtoPedia提出YouTube）を先に作る＝鉄田タスク継続／②60秒ピッチ内デモは最終選考通過後に作る想定で今は着手しない** (旧WP8.1) | 🟡台本✅・①録画優先／②保留 |
| C6.2 | デモのデータ戦略（seed投入 or ライブ） | デモ録画で毎回同じ結果が出るよう、データの準備方法（仕込み or 本番）を決める | 鉄田・一瀬 | W5（7/6–12） | 全機能 | 録画再現性確保（I-14） (旧WP8.2) | 🔜着手前 |
| C6.3 | デモ録画（予約→入荷を撮る） | 予約→入荷の流れを録画・編集して提出用の動画にする | 鉄田 | W5（7/6–12） | C6.1,C6.2 | 提出動画 (旧WP8.3) | 🔜着手前 |
| C6.4 | ピッチ図解（自律アーキ・必然性） | 自律アーキ・AIの必然性・将来構想を説明するスライドを作る | 鉄田 | W4–W5（6/29–7/12） | — | スライド (旧WP8.4) | 🔜着手前 |
| C6.5 | README仕上げ（再現可能性） | 他人が再現できるよう、起動手順・構成図を整える | 鉄田 | W5（7/6–12） | 全体 | 起動手順・構成図 (旧WP8.5) | 🔜着手前 |
| C6.6 | **ProtoPedia提出・リポジトリpublic化（最終提出）** | ProtoPediaに作品ページを公開し、公開リポを添えて7/10締切までに最終提出する | 鉄田・一瀬 | W5（7/6–12） | C6.3,C6.5,C6.7 | ProtoPedia作品ページ公開＋7/10締切（P-3）。※公開クリーンリポ／図マスク版は WBS 外（別途作成・旧C6.8を2026-06-11に切り出し） (旧WP8.6) | 🔜着手前 |
| C6.7 | **ProtoPedia作品ページ作成（ストーリー/画像5/システム構成/動画/各フィールド）** | 提出先ProtoPediaの作品ページを作る。草案一式は作成済＝あとは実フロントのスクショと各URL差し替え | 鉄田 | W5（7/6–12） | C6.3 | 草案＝`publishr_other/Protopedia提出/`（ストーリーv2・画像プラン・記入シート）。体験画像①②③は**実フロントのスクショ（佐倉/7名）**に差替（P-7）／動画＝YouTube限定公開／必須技術＝GEAP明記（P-6） | 🟡草案✅・本番化残 |

---

# 時間軸ビュー（参考）

> ※ここは**カテゴリWBSを時間軸で見たい時の参考**。タスクの正本は上の A/B/C 各表。週ラベルの実日付は本書冒頭の「予定週の凡例」および [master-schedule.md](master-schedule.md) を参照。

## 週次マッピング（カテゴリ×週・実日付）
| カテゴリ＼週 | W0<br>6/1–7 | W1<br>6/8–14 | W2⚡<br>6/15–21 | W3<br>6/22–28 | W4<br>6/29–7/5 | W5<br>7/6–12 |
|---|---|---|---|---|---|---|
| A 要件定義・設計 | A5.1 | A3.2/A5.2 | | | | |
| B 環境・インフラ | B1.1/B1.3/B2.1 | B2.2/B3.1/B3.3 | B1.2 | | B3.2/B4.1 | |
| C0 ローカル基盤(H0) | **C0.1/C0.2✅** | | | | | |
| C1 エージェント(モードA) | **C1.0.1✅** | **C1.1-C1.3✅** | **C1.4-C1.7✅**※ | | | |
| C2 エージェント(モードB) | | **✅C2.1-2.3（前倒し・6/9）** | | ~~C2.1-2.3~~ | | |
| C3 データ基盤（鉄田） | **✅C3.1/3.4/3.5**（6/6完了） | | C3.2 | C3.3 | | |
| C4 フロント | | | C4.1-4.3 | C4.4-4.6 | C4.7 | |
| C5 品質・観測・運用 | C0.1(mock Eval)✅ | C5.1/5.7/5.8 | C5.2/5.4 | C5.9 | C5.3(GEAP)/5.5/5.6 | |
| C6 デモ・提出 | | C6.1 | | | C6.4 | C6.2/6.3/6.5/6.6/**6.7** |

## マイルストーン（実日付・WBS対応）
| MS | 主WBS | 週・期日 | 判定 |
|---|---|---|---|
| M0 | **C0.1/C0.2** | W0末（6/7頃） | mock回帰＋実装シーム完了（**2026-06-06 達成**） |
| M1 | **C1.0.1** | W1末（6/14頃） | 実Vertex MiniLoop（**C1.0.1ゲート**・最大リスク解消）（**2026-06-06 達成・W0前倒し**） |
| **M2** | **C1.1–C1.3＋C4** | **W2末（6/21頃）** | ✅**2026-06-09 達成（前倒し）**: 観測→企画→棚に並ぶ＝山場/撤退判定点クリア（PR#4・Cloud Run/Firestore縦通し・トリガー実モードA） |
| M3 | **C1.7/C2** | W3末（6/28頃） | ✅**完了（2026-06-10・前倒し）**: C2.1-2.3＝予約→Pub/Sub→本文編集ループ(最高3R)→published（PR#6-9）＋**C1.7 Scheduler本番**（`publishr-honmei`・水/土6:00 JST・OIDC→Cloud Run trigger→佐倉Firestore自律入荷・実機検証済）。**残＝serendipity(日)差別化の小follow-upのみ** |
| 🔒 機能凍結 | — | 6/30 | 以後は品質向上・デモ磨きのみ |
| M4 | **C5/B3** | W4末（7/5頃） | ✅**ほぼ完了（2026-06-11・前倒し）**: C5.9 resilience＋C5.6 Langfuse2ループ＋C5.3 Evalゲート(7/8停止)＋B4.1 IaC＋**B3.2 CD自動デプロイ(mainマージ→Cloud Run・WIF・実機✅)**＋B3.1 CI（PR#13・#15・#17）。**残＝C5.3 GEAP本番judge(課金)・C5.4/5.5 judge再現性/閾値調整(鉄田)** |
| M5 | **C6** | W5（7/9頃） | 録画＋README |
| 🚩 M6 | **C6.6** | 7/10（厳守） | public化・最終提出 |

> **遅延時の原則**: W2のM2を死守（横に作り込まず縦に細く通す）。詰まればSTEP2(C1.3)のみLangGraphへ（ADK §8）。Stretch（粒度選択/ES/ループB実装）はW5余力次第。
