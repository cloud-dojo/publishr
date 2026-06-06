# Publishr 全体構築プラン — git＋ローカルmock から ハッカソン提出まで（実装順序つき）

## Context（なぜこのプランか）

**Publishr** =「日々のデータ（Drive/Calendar/Tasks）を観測し、いま何を読むべきか・誰に書かせるかを自律判断して出版する専属AI出版社」。ハッカソン提出（締切 **7/10**、機能凍結 **6/30**）。

**実態（ユーザー申告）**: いまは **git リポジトリ＋コード骨格（すべて mock/canned）だけ**。Firestore・Cloud Run などクラウド実体は未構築/未デプロイ。
> ⚠️ **docsとの齟齬**: `docs/infra/gcp-setup-log.md` は「GCP `publishr-498123` 構築済（API有効化・Firestore・バケット・SA・Secrets・Firebase Blaze・Langfuse・予算アラート）」と記録。実態と食い違うため、本プランは **Phase 1 を「現状確認→不足分を構築」** とし、構築済みでもゼロでも成立させる。

**いま在るもの（コード骨格・すべてmock）**
- `apps/web`（Next.js）= 書店UI **14ルート mock 実装・ビルド緑**。Firebase Auth/Firestoreプロバイダ実装済（mock時休眠）。
- `agents/publishr_agents`（ADK配線）= `Sequential(observe→reader→Parallel(3企画)→選抜→著者→装丁)`・`InMemoryRunner`・**出力は決定的canned**・`test_pipeline.py`あり。**実LLM/実escalate/v2フロー未**。
- `apps/api`（FastAPI BFF）= books/plans/personas/users/pipeline ＋ reservation/feedback/reading サービス ＋ `mock_repository`。**Firestore未**。
- `packages/prompts` 完成プロンプト11本（`.md`・未配線）／`eval/eval_set.yaml` 8件／`scripts/eval_harness.py`（自作・決定的judge）。

**ユーザー指示**: 全トラック（①ADK実escalate ②実LLM ③フロント仕上げ ④Evalゲート）を**実LLM接続まで含め**、**全体の作り方と実装順序**を示す。

### 前提検証（Planエージェントが `.venv` の **google-adk 2.1.0** ソースで確認済）
`LoopAgent(max_iterations)` は `event.actions.escalate` でループ脱出＝**スコア閾値差し戻しの脱出機構**。`LlmAgent` は `model/instruction(callable可)/output_schema/output_key/tools` を持ち、`output_schema`+`google_search` が**共存可**。⚠️ `{{var}}` 注入はトップレベルのみ（`{{a.b}}` ネストは不可→`render.py`で自前展開）。**結論: LangGraphフォールバックは不要**（ただしSTEP2は1モジュールに隔離し差し替え口は残す）。

---

## 設計原則（全フェーズ共通の不変条件）
1. **mock経路 = 常に回帰の床（always-green）＆デモ安全網**。`PUBLISHR_LLM=mock`/`DATA_SOURCE=mock`/`NEXT_PUBLIC_DATA_SOURCE=mock` でクラウド・認証・課金ゼロでフル動作。既存テストと `make eval/pipeline/smoke/verify` を常に緑に保つ。
2. **縦に細く通す（W2 E2E死守）**。横の作り込みより「観測→企画→棚→予約→執筆→読める」の縦串を最優先。
3. **最大リスク先行**: 実LLM escalateループ（ADK疎通）をPhase 2で先に潰す。詰まればSTEP2のみLangGraph。
4. **撤退ライン**: W1=ADK疎通／W2=E2E縦通し。通らなければPatentSentinelへ即退避（事前合意）。
5. **運用リスクを前倒し**: 最小Cloud Runデプロイ・最小CI・小さなEval・Firestore rules検証はP3/P4から入れる。P6で初めて触らない。
6. **コード規律**: small-files（200–400行・最大800）、immutability、入力検証、秘密はSecret Manager/env。
7. **コスト暴走はコード側で止める**: Budget通知は検知の保険であり、主防御は `PUBLISHR_LLM=mock` 既定、dev実行縮小、`max_iterations`/冊数/ページ数/Imagen/timeout/推定コスト上限、公開APIの認証・許可uid・連打防止で担保する。

### ハードゲート（ここを越えない限り次へ進まない）
1. **P0a: mock回帰復旧ゲート** — `make verify`＋`make eval`＋`make pipeline`＋`make smoke` が全緑。特に `eval/eval_set.yaml` と `scripts/eval_harness.py` の形式不整合を先に直し、mockの床を復旧する。未達ならP0b/P1/P2へ進まない。
2. **P0b: 実装シーム＋コストガード完了ゲート** — v2 I/O schema、state keys、prompt loader/registry/render、LLM provider、`PUBLISHR_LLM` dispatcher が入り、mock時の挙動差分ゼロ＋loader単体テスト緑。加えて `PUBLISHR_LLM=mock` 既定、dev/prod実行プロファイル、実LLMの上限値（iterations/books/pages/images/timeout/estimated cost abort）が設定で管理される。未達ならP2へ進まない。
3. **P2/M1: ADK実LLMランタイムゲート** — MiniLoopが実Vertexで再実行可能、score差し戻し→再提出→`escalate`脱出、Langfuse trace、成功JSON、`@pytest.mark.vertex` 最小テストまで揃う。実行はdevプロファイル（最小件数・短文・Imagenなし）で、1 run の推定コスト/トークン/実行IDが残る。未達ならP3へ進まない。
4. **P4前: 公開前セキュリティ/コストゲート** — Cloud Runを外部公開・`PUBLISHR_LLM=vertex`・`DATA_SOURCE=firestore` の組み合わせに進む前に、Firebase IDトークン検証、Firestore rulesデプロイ、OAuth `state` 検証、手動トリガー許可uid、連打防止/最小レート制限、Vertex IAM境界を全て確認する。未達ならAPIを公開しない。

---

## 実装順序（要約・上から順に着手）

| Phase | 山場 | 目的 | 主担当 | クラウド/課金 |
|---|---|---|---|---|
| **P0a** mock回帰復旧 | **H0a** | `make eval/verify/pipeline/smoke` を全緑に戻す | 鉄田 | なし |
| **P0b** 実装シーム敷設 | **H0b** | v2 I/O・prompt loader・LLM dispatcher・コストガードを入れ、mock挙動差分ゼロ | 鉄田 | なし |
| **P1** GCP基盤 確認/構築 | — | 現状確認→不足分プロビジョニング＋ADC認証 | 鉄田(GCPオーナー) | 基盤のみ・微小 |
| **P2** ADK疎通(MiniLoop) | **M1/H2** | 実LLM escalateループ実証（最大技術リスク・P3進行条件） | 一瀬 | LLM少 |
| **P3** モードA全STEP+Firestore+最小運用 | — | 観測→…→棚に5冊draft（実LLM・実DB）＋rules/Eval/最小デプロイの足場 | 一瀬 | LLM中 |
| **P4** E2E縦通し（ブラウザ） | **M2★** | 観測→企画→棚 をブラウザで縦串＋最小Cloud Run疎通＋フロント仕上げ | 鉄田・一瀬 | LLM中 |
| **P5** モードB執筆（段階導入） | **M3** | 予約→手動1冊執筆→非同期化→Scheduler自律の順で読める状態へ | 一瀬 | LLM大 |
| **P6** 品質/観測+CI/CD完成 | **M4** | Evalゲート(GEAP)+Langfuse+自動デプロイ+IaCを完成形へ | 一瀬・鉄田 | LLM中 |
| **P7** デモ/提出 | **M5/M6** | 録画+README+ProtoPedia+公開リポ→7/10提出 | 鉄田・一瀬 | — |

> **担当凡例**: 鉄田=Claude Code（フロント/プロンプト/Eval設計/デモ）・一瀬=友人（ADK/基盤/DevOps）。本プランは全トラック横断のため Claude Code が大半のコードを駆動可。ただし**GCPコンソール操作・認証情報・GitHubオーナー操作（App Hosting連携）はユーザー/一瀬の手が必要**。

### インフラ構築の段階（いつ何ができるか）
| 段階 | できるインフラ | 構築/接続の粒度 | 次フェーズへの意味 |
|---|---|---|---|
| **P0a/P0b** | なし（ローカルmockのみ） | `.env` は全mock。GCP/Firestore/Cloud Runへは接続しない | クラウド無しで常時回帰できる床を作る |
| **P1** | GCP基盤の器 | Project/API/Firestore/GCS/SA/Secret/Firebase Auth/OAuth/予算/ADCを確認し、不足分だけ作成 | P2でローカルからVertex Geminiを呼べる |
| **P2** | Vertex/Langfuse疎通 | Cloud Run等はまだ作らない。ローカルCLIからVertex Gemini + google_search + Langfuse traceを検証 | 実LLM/ADKが本当に動くことを証明する |
| **P3** | Firestore実データ層 + 最小CI/デプロイ足場 | APIはまだローカル中心。`DATA_SOURCE=firestore`、rules/index、Firestore保存、Cloud Run手順/Dockerfile雛形 | 実DBに棚データを残せる |
| **P4** | API最小Cloud Run | APIだけCloud Runに載せ、`/health`・planning trigger・Firestore保存を手動確認 | ローカル外でもモードA縦串が通る |
| **P5** | 本番寄り実行基盤 | Artifact Registry、API/worker/planning Job、Pub/Sub、GCS本文保存、Cloud Scheduler、必要ならFirebase App Hosting | 予約→執筆→公開と自律棚更新が動く |
| **P6** | 完成形の運用基盤 | GitHub Actions→Cloud Build→Cloud Run、GEAP Eval gate、Terraform、監視/コスト/リトライ方針 | pushから自動デプロイまで閉じる |

---

## Phase 0 — ローカル基盤固め（クラウド・課金なし）

**目的**: mock経路を完全に緑にし、実装の継ぎ目を敷く。挙動は一切変えない。

- **P0a mock回帰復旧（H0a・最優先）**:
  - `make setup`→`.env` を `.env.example` から作成（全mock）→`make dev`（API+Web）→`make smoke`/`make verify`/`make pipeline`/`make eval` を緑に戻す。
  - 現状の最優先修正: `eval/eval_set.yaml`（v2）と `scripts/eval_harness.py`（旧形式）の不整合を直し、mock用の決定的Evalを復旧する。GEAP/Vertex Eval化はP6でよく、ここではオフライン回帰の床を守る。
  - **H0aゲート**: `make verify`＋`make eval`＋`make pipeline`＋`make smoke` が全緑。未達ならP0b/P1/P2へ進まない。
- **P0b 実装シーム敷設（H0b・挙動変更ゼロ／Track A の足場）**:
  - 新Pydantic I/Oモデルを `packages/shared-schema/py/publishr_schema/agent_io.py` に追加：`PlanProposal`(8項目)/`LeaderVerdict`(4観点score・belowFloor・decision・rejectionFeedback・approvedPlan)/`SubReaderContext`・`SubMarket`・`SubThemeInsight`/`ReaderProfile3Layer`(base/currentWork/readingBehavior=新設・旧flat ReaderProfileは温存)/`GeneratedPersonaSet`/`BookDraft`/`EditorVerdict`/`BodyVerdict`。`__init__`からexport。
  - `agents/publishr_agents/state_keys.py` を拡張（planDraft/leaderVerdict/rejectionFeedback/approvedPlan/sub*/generatedPersonaSet/editorFeedback/editorVerdict/round/theme_kind）。
  - `llm/provider.py`（`model_for(role)→Geminiモデルid`・Pro/Flashハイブリッド表を一元化）。
  - `prompts/loader.py`（`.md`からsystem/user_template/✅good-example抽出・`lru_cache`・`PUBLISHR_PROMPTS_DIR`維持）＋`prompts/registry.py`（step→{model_role,is_scoring,fewshot_always_on,output_schema,output_key}）＋`prompts/render.py`（`make_instruction`=InstructionProvider・ネスト変数自前展開＋`PROMPT_FEWSHOT`）。
  - `apps/api/.../config.py` に `prompt_fewshot` と実行プロファイル（`dev`既定/`prod`明示）を追加。devは本文3〜5p・1run 1〜2冊・Imagen mock・編集1R・短timeout、prodはデモ/録画時のみ明示。
  - `pipeline.build_pipeline()` を `PUBLISHR_LLM` 分岐の**dispatcher化**（mock時は今日と同一木）。`PUBLISHR_LLM` 未指定は `mock`、`vertex` は明示opt-in。`canned.py`/`agents.py`/`result.py`(mockロジック)/`authoring.py` は不変。
  - 実LLM呼び出しの共通ガードを追加：`max_iterations`、最大冊数、最大本文ページ、Imagen実行フラグ、timeout、実行ID、推定token/costログ、推定上限超過時abort。Budget通知は別保険であり、アプリ内の暴走停止を主防御にする。
  - **H0bゲート**: mock時の既存挙動差分ゼロ、既存テスト全緑（vertexコード未到達）、`prompts/loader`が全11本から非空systemを返す単体テスト緑、dev実行上限の単体テスト緑。未達ならP2へ進まない。
- **成果物**: 完全動作するローカルmockアプリ＋実装シーム完備。

---

## Phase 1 — GCP基盤: 現状確認 → 不足分を構築（基盤のみ・課金微小）

> ⚠️ docsは構築済と記録。**まず実在を確認し、無いものだけ作る**。GCPコンソール/CLIはユーザー（GCPオーナー＝鉄田）。WSL2側 gcloud を使用（Norton回避・ERRORS.md）。

- **P1-1 確認**: `gcloud projects describe publishr-498123`／有効API一覧／`gcloud firestore databases list`／`gsutil ls`／SA・Secrets・Firebase の存在確認。
- **P1-2 不足分プロビジョニング**:
  - API有効化: `aiplatform`,`run`,`cloudbuild`,`firestore`,`storage`,`pubsub`,`cloudscheduler`,`identitytoolkit`,`secretmanager`,`artifactregistry`。
  - Firestore（`(default)`・Native・`asia-northeast1`）／GCSバケット `publishr-contents-498123`（非公開）。
  - SA: `publishr-runner`（aiplatform.user・run.invoker・datastore.user・storage.objectAdmin・secretAccessor）＋ `publishr-ci-deployer`（run.admin・cloudbuild.editor・iam.serviceAccountUser・artifactregistry.writer・storage.admin）。**eval用に `roles/aiplatform.user` 必須**。
  - Secret Manager: `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`/`LANGFUSE_HOST`/`GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`。
  - Firebase: プロジェクト紐付け・Blaze・Auth(Googleプロバイダ)有効化。予算アラート¥10,000（50/90/100%）。
  - OAuth同意画面（外部・本番未審査）＋スコープ3つ（`drive.file`/`calendar.readonly`/`tasks.readonly`）＋Webクライアント。リダイレクトURIは当面 `localhost`、backendデプロイ後に本番URI追記（B1.2）。
- **P1-3 ローカル実LLM疎通の足場**: `gcloud auth application-default login`／env `GOOGLE_GENAI_USE_VERTEXAI=TRUE`・`GOOGLE_CLOUD_PROJECT=publishr-498123`・`GOOGLE_CLOUD_REGION=asia-northeast1`（evalのみ `us-central1`）。最小の「hello Gemini」呼び出しが通ることを確認。Vertex/Gemini/Imagen/Evalのリージョン・クォータ・課金上限も確認し、詰まりをP2前に潰す。
- **P1-4 インフラ台帳**: `docs/infra/gcp-setup-log.md` を実態に合わせて更新し、作成済み/未作成/意図的に後回し（Cloud Run Job・Scheduler・Pub/Sub等）を明記。二重作成と課金事故を防ぐ。
- **GitHubオーナー依存（一瀬・並行/後回し可）**: App Hosting の GitHub App 連携・Cloud Build GitHub接続は所有者のみ。**回避＝CI/CD方式B**（GitHub Actions→`gcloud builds submit`）でオーナー依存を外す（P6で実装）。
- **成果物**: GCP基盤レディ・ADCでローカルからGemini呼べる。Firestore/GCS/SA/Secrets/Firebase/OAuthの実在状態が台帳化され、P2/P3で使う接続情報が揃う。

---

## Phase 2 — W1 ADK疎通: 実escalateループ + 実LLM（★最大リスク・M1）

**目的**: `adk-control-flow.md §7` の MiniLoop を実LLMで実証。ここが全体の関門。

- **P2開始条件（H0b必須）**: P0a/P0bが両方通過済みで、mock回帰が緑、v2 schema/prompt/dispatcherの差し替え口が存在すること。ここを満たさない状態でMiniLoopを作らない。
- **P2-1 MiniLoop**: `LoopAgent(max_iter=3)` ＝ 調査サブ1(Flash+`google_search`) → owner1(Flash) → leader1(Pro) → `LoopBreakAgent`（小custom BaseAgent）。`prompts/` 経由で実プロンプト注入。
- **P2-2 escalate配線**: leaderが `LeaderVerdict` を `output_key="leaderVerdict"` に出力 → `LoopBreakAgent` が `rejectionFeedback`/`approvedPlan` を state_deltaへコピーし、`decision=="approve"` で `EventActions(escalate=True)`。round3は belt-and-suspenders（プロンプト帯「最良案を必ず承認」＋コード帯「最終iterでrevise残なら現planDraftをapproved昇格」）。
- **P2-3 Langfuse計装**: 「スコア化→閾値未満で差し戻し→再提出→採用」遷移（score/round）＋grounding取得URL/クエリを1トレースに。
- **P2-4 コストガード実証**: devプロファイル固定（最小入力・短文出力・Imagenなし）で実行し、1 run ごとに `run_id`、model、round、入力/出力token概算、推定cost、abort理由をログ化。推定上限を超えたらVertex呼び出し前に停止する。
- **P2-5 インフラ利用範囲**: 利用するクラウドはVertex Gemini（必要に応じてgoogle_search grounding）とLangfuseのみ。Cloud Run/Firestore/Pub/Sub/Schedulerはまだ本線に入れず、ADKランタイムリスクだけを切り出す。
- **DoD（W1/M1/H2ゲート）⚠️ランタイム検証必須**: ①groundingが実ソース取得 ②owner が sub読む ③leader が score付verdict ④score<70で再ループ（rejectionFeedback反映）⑤score≥70でescalate脱出 ⑥round3強制採用。Langfuseに反復→脱出が残る。
- **再現性成果物**: `scripts/run_miniloop.py`（または同等CLI）で誰でも再実行可能にし、成功時サンプルJSON・失敗時ログ・`@pytest.mark.vertex` の最小テストを残す。単に「一度動いた」状態で次へ進まない。
- **H2ゲート運用**: H2未達ならP3（STEP2フル/Firestore/全STEP実LLM）へ進まない。3日詰まったらSTEP2のみLangGraphへ切替判断し、それでもH2を満たしてからP3へ進む。
- **詰まったら**: STEP2のみ LangGraph（`step2_planning.py` 隔離済で1ファイル差し替え）。
- **成果物**: 実LLM escalateループ実証済み＋再実行可能なMiniLoop検証一式。STEP2本体の拡張だけで済む状態。

---

## Phase 3 — モードA 全STEP（実LLM）+ Firestore永続化 + 最小運用

**目的**: 観測→読者分析→企画(差し戻し)→キャスティング→プレビュー編集→装丁 を実LLMで通し、棚に5冊 draft。永続化をFirestoreへ。P6で事故らないよう、rules/Eval/最小デプロイの足場もここで作る。

- **P3-1 STEP2フル**（`vertex/step2_planning.py`）: 調査サブ3体（A=no-tool/B・C=Flash+google_search・初回Rのみgate）＋owner/leader Pro＋themeKind分岐。`vertex/state_bridge.py` で `LeaderVerdict` 履歴→`RejectLogEntry`／`PipelineResult` に **additive で `leader_verdicts` 追加**（既存契約不変）。
- **P3-2 STEP1+STEP0**: `ReaderAnalystAgent`(Pro→`ReaderProfile3Layer`)＋`ObservationTool`（batch・当面 `canned.aggregate_keep_notes` 再利用／実Drive観測はP4）。
- **P3-3 STEP3+STEP4**: `PersonaGeneratorAgent`(Pro・5人・count不一致リトライ)＋`PreviewEditLoop ×5`=`LoopAgent(max_iter=2)`（Author Pro+Editor Pro・approve/revise via editorFeedback）→BookDraft×5。
- **P3-4 STEP5**: `CoverParallel`（Flashで coverPrompt → Imagenは `ENABLE_IMAGEN` フラグ・既定mock URL）。
- **P3-5 Firestore永続化（C3.5/C3.1/C3.4）**: `apps/api` の `RepositoryProtocol` に Firestore実装を追加（`mock_repository` と同IF）。`firestore-security-rules.md`/`firestore.indexes.json` をデプロイ。`DATA_SOURCE=firestore` で plans/books/personas/observations を保存。`ownerUid` 規約。
- **P3-6 Firestore境界テスト**: `ownerUid` 不変・collection/field単位の書込境界を明文化。クライアント直書き可は `initialProfile`/`highlights`/`feedback`/`favoriteAuthors` 等に限定し、`books`/`plans`/`personas` は原則サーバー更新。rules unit test または emulator test を追加。
- **P3-7 API認証境界**: FastAPI側にFirebase Admin SDKの共通依存を入れ、`/healthz` 以外のAPIで `Authorization: Bearer <Firebase ID token>` を検証する。サーバ側はトークン由来の `uid` を使い、リクエストbodyの `userId` は信用しない。未認証mock BFFのままCloud Run公開・Vertex接続へ進まない。
- **P3-8 小さなEval/CI/デプロイ足場**: Mode Aの最小Eval（schema妥当性・score閾値・5冊生成）を `make eval` とは別に用意。`.github/workflows/ci.yml` の雛形（lint/test/eval-mock）と、APIだけのCloud Run最小デプロイ手順またはDockerfileを先に置く。
- **P3-9 インフラ状態**: ここで初めてアプリ本線がFirestoreを使う。Cloud Runはまだ「手順/雛形」までで、常時稼働サービス化はP4。Pub/Sub/Scheduler/WorkerはP5まで作らない。
- **P3-10 実行縮小の維持**: 開発runは `dev` プロファイル（1〜2冊・短文・Imagen mock・編集1R）で通し、5冊/Imagen実生成はゲート確認・録画前の明示実行に限定する。
- **ゲート**: `PUBLISHR_LLM=vertex`＋`DATA_SOURCE=firestore` で run→5冊 draft（入荷理由付き）がFirestoreに。Firestore rules test・小さなMode A eval・mock経路が緑。vertexテストは `@pytest.mark.vertex`（creds時のみ）。5冊runは1回ごとの推定cost/traceを確認してから再実行する。
- **成果物**: 実LLM＋実DBのモードAパイプライン、Firestore安全境界、最小Eval/CI/デプロイの足場。

---

## Phase 4 — E2E縦通し（ブラウザ）＋フロント仕上げ（★W2山場・M2）

**目的**: ブラウザで「観測→読者分析→企画(差し戻し)→棚に5冊入荷（理由付）」を縦串。全体の成否を決める。

- **P4-1 フロント本接続（C4.9）**: Firebase Auth（Googleログイン）＋Firestore直購読（棚/本詳細/読書メタ）＋直書き（initialProfile/ハイライト/FB/favoriteAuthors arrayUnion）。予約は `bff-provider.ts`→`POST /api/reserve`。`NEXT_PUBLIC_DATA_SOURCE=firestore`。設定値（`NEXT_PUBLIC_FIREBASE_*`）受領。
- **P4-2 観測の実接続**: `GET /api/auth/google/start`→`callback`（Firebase IDトークン検証、短命・署名付き・uid紐付き `state` 検証、refresh_tokenをSecret Manager保存、トークン/認可コードをログ出力しない）＋**Drive Picker UI**（`drive.file`は列挙不可のため選択式）＋実Drive/Calendar/Tasks観測。**OAuthが間に合わなければfixture観測のまま縦通しを優先**（E2E死守）。
- **P4-3 手動トリガー**: `POST /api/trigger/planning`（themeKind/runAnalysis・デモ垢限定認可・即202）。Vertexコスト暴走防止のため、許可uid外は `403`、最低限のレート制限/連打防止、同一uidの実行中ロック、dev/prodプロファイルのサーバ側固定を入れる。bodyの `userId` や `profile=prod` 指定は信用しない。
- **P4-4 最小Cloud Run疎通**: APIだけCloud Runに載せ、`/health`・`POST /api/trigger/planning`・Firestore保存までを手動で確認。本番完成ではなく、認証/Secret/env/リージョン差分を早期に出す。
- **P4-5 フロント仕上げ（C4.8）**: 14ルートのレイアウト崩れ/行ずれ/全画面QA（`apps/web/src/app/*`・`components/*`）。`map/` が `leader_verdicts`(score/round) の却下→採用を描画＝**基準1の画**。
- **P4-6 インフラ状態**: API Cloud Runは最小1サービスのみ。Artifact Registry/Cloud Buildは手動デプロイでよく、Cloud Scheduler/Worker/App Hostingの完成はP5以降。目的は「本番完成」ではなく、env/Secret/IAM/リージョン差分を早期に出すこと。
- **ゲート（M2★）**: `make dev`＋ブラウザで観測→企画(revise)→棚5冊入荷を縦通し。加えてAPI最小Cloud Runでplanning手動トリガーが1回通る。公開URLに対して、未認証リクエストが `401`、他ユーザー資源が `403`、許可uid外のtriggerが `403` になることを確認する。**ここが撤退判定点**。
- **成果物**: 動くE2Eスライス（モードAの体験が成立）＋最小クラウド疎通実績。

---

## Phase 5 — モードB執筆（段階導入）+ 自律トリガー（M3）

**目的**: 予約→執筆ループ→読める、を手動1冊から始めて非同期化し、最後にSchedulerで自律起動する。P5内で一気に全部作らない。

- **P5-1 手動1冊執筆（最小M3a）**: `mode_b/` に BodyEditLoop を作り、`scripts/run_body_once.py`（または同等CLI）で1冊だけ生成→GCS保存→`read/[bookId]`で読める。開発中は本文3〜5p・1R固定、100p/3Rは録画前の明示実行のみ。`LoopAgent(max_iter=3)`（Author+Editor+BodyLoopBreak）。**大型生成物をstateに溜めない**（章本文はGCSへ・stateはref+prevChapterSummary+weakChapters[]のみ）。**弱い章のみ改稿**。
- **P5-2 予約API接続（M3b）**: `reservation_service.advance` の `write_body` を `mode_b.worker.run_body_pipeline` dispatcherに置換（mock=既存`_MAKASE_BODY`／vertex=ループ）。`status==writing|published` skip-guard維持。`POST /api/reserve` はまず同期/手動キックで1冊成功を優先し、同時5冊transactionは後続で入れる。
- **P5-3 非同期実行（M3c）**: `POST /api/reserve`（**同時5冊 Firestore transaction**・I-16/I-20）＋Pub/Sub `book-writing` 発行＋**WritingWorker（Cloud Run Service）**。GCS署名付きURLで本文保護。worker側にも同時実行数・timeout・重複job skip・推定cost上限を置き、API側ガードだけに依存しない。
- **P5-4 自律起動/本番配置（M3d）**: Dockerfile（API/worker/planning Job）→Artifact Registry→Cloud Run。**モードA=Cloud Run Job**（曜日別 themeKind/runAnalysis パラメータ）。**Cloud Scheduler 3ジョブ**（土=観測+本命／水=本命／日=セレンディピティ）。backend本番URIをOAuthに追記（B1.2）。
- **P5-5 フロント本番ホスティング**: Firebase App Hosting（`apps/web`・`apphosting.yaml`・**GitHub App連携=一瀬**）or Cloud Run。
- **P5-6 インフラ状態**: ここで初めて非同期・自律実行基盤を本線化する。`API Cloud Run`、`WritingWorker Cloud Run Service`、`Planning Cloud Run Job`、`Pub/Sub book-writing`、`GCS本文保存`、`Cloud Scheduler` が揃う。まず手動1冊→予約API→Pub/Sub worker→Schedulerの順で段階投入する。
- **ゲート（M3）**: M3a=手動1冊が読める、M3b=予約APIから1冊が読める、M3c=Pub/Sub workerで読める、M3d=Schedulerで自律的に棚更新。各小ゲートを通してから次へ進む。
- **🔒 6/30 機能凍結**（以後は品質・デモ磨きのみ）。
- **成果物**: 手動1冊→予約API→非同期worker→Scheduler自律、の順で積み上がった「読める」モードB。

---

## Phase 6 — 品質・観測 + CI/CD + IaC（M4）

**目的**: P3/P4で先に置いた最小Eval/CI/デプロイ足場を、Observability L4（継続Eval）と自動デプロイの完成形へ引き上げる。

- **P6-1 Evalゲート（GEAP・C5.3/I-21）**: 自作 `scripts/eval_harness.py`（mock即時・オフラインCIの床）は残す。**Vertex AI Gen AI Evaluation Service版**を併設（`eval_judge.md` を LLM-as-judge・`vertexai.evaluation`・**region=`us-central1`**）。8件、本命総合<70 / 8件中7件で停止。再現性テスト（境界ケースで閾値70近傍）。
- **P6-2 Langfuse**: 2ループ（企画スコアループ＋編集ループ）＋grounding URL/クエリ＋Eval結果を可視化。
- **P6-3 CI/CD完成**: P3の最小CIを拡張し、`.github/workflows/deploy.yml`（lint→Eval Gate→Cloud Build→Cloud Run）へ。**方式B**（Actions→`gcloud builds submit`）でオーナー依存回避。GitHub Secrets 6本（GCP_PROJECT_ID/GCP_SA_KEY/OAUTH×2/LANGFUSE×2）。
- **P6-4 IaC**: `terraform/`（Cloud Run/Job/Scheduler/Pub-Sub/IAM）。Firestore/バケット/Auth/Secret値はIaC外。
- **P6-5 運用**: dev/prodフラグ（ページ少/画像ダミー/冊数少）＋コスト実測（¥10,000耐性）＋エラー/リトライ/冪等/タイムアウト最小方針。Budget通知は既存設定を前提に、アプリ側の実行ログ（run_id/model/token/cost/abort）と突き合わせる。Discord通知は任意の見落とし防止で、主防御はコード上限・認証・許可uid・連打防止とする。
- **P6-6 インフラ状態**: P1〜P5で手作業/手順化した構成を、GitHub Actions・Cloud Build・Terraformで再現可能にする。Secret値、Firestoreデータ、Firebase Auth設定そのものはIaC外に残し、参照名と必要権限だけコード化する。
- **ゲート（M4）**: push→Evalゲート→自動デプロイ。プロンプト劣化で停止を実証。
- **成果物**: 継続Eval付きCI/CD＋必然性の証跡可視化。

---

## Phase 7 — デモ・提出物（M5/M6）

- **P7-1 デモデータ戦略**: 録画再現性のためseed投入（佐倉美咲・部下7名）。
- **P7-2 録画**: 審査用2.5分＋ピッチ60秒（台本✅）。必然性3証跡（却下→再提出を画に）を必ず収める。
- **P7-3 README/スライド**: 起動手順・構成図・自律アーキ。
- **P7-4 ProtoPedia作品ページ（C6.7）**: ストーリー・**実フロントスクショ5枚**・システム構成図・YouTube限定公開URL・GEAP明記。
- **P7-5 公開クリーンリポ（C6.8）**: 履歴なし新規リポ・実名/projectID/デモ垢スクラブ・docs全除外・prompts公開・MIT・図の内部値マスク。
- **ゲート（M6）**: **7/10 厳守**で ProtoPedia公開＋公開リポ提出。

---

## 主要な依存・並行関係
- **直列の幹**: P0a(H0a)→P0b(H0b)→P1→P2(M1/H2)→P3→P4(M2)→P5a→P5b→P5c→P5d(M3)→P6(M4)→P7(M6)。
- **並行可**: フロント仕上げ(P4-5/C4.8)・プロンプト実テスト(C5.1)・デモ台本/ProtoPedia草案・最小CI/デプロイ足場(P3-8) は P2/P3 と並行（鉄田）。GCPオーナー操作(P1)・GitHubオーナー操作(App Hosting/Cloud Build) は ユーザー/一瀬の手番。
- **ブロッカー**: H0a未達なら全開発停止してmock回帰復旧を優先。H0b未達ならP2停止。H2未達ならP3停止。実LLM/Firestore/デプロイ系は GCP認証・課金が前提（mock経路は不要）。App Hosting自動連携は一瀬のGitHubオーナー操作待ち（方式Bで回避可）。

## 検証（E2E・各ゲート）
1. **H0a / mock回帰復旧**: `make verify`＋`make eval`＋`make pipeline`＋`make smoke` 緑。未達なら他作業へ進まない。
2. **H0b / 実装シーム＋コストガード完了**: v2 I/O schema、state keys、prompt loader/registry/render、LLM dispatcher が存在し、mock挙動差分ゼロ。`prompts/loader` 全11本テスト緑。`PUBLISHR_LLM=mock` 既定とdev実行上限もテスト緑。
3. **M1/H2（P2）**: MiniLoop実行→Langfuseで反復→escalate脱出（score/round/round3強制採用）。再実行CLI・成功JSON・vertex最小テストも残す。未達ならP3へ進まない。
4. **コストガード**: `PUBLISHR_LLM` 未指定はmock、devプロファイルは1〜2冊/短文/Imagen mock/1R、実LLMはiterations・timeout・推定cost上限でabortできる。公開APIはFirebase IDトークン・許可uid・連打防止・実行中ロックを確認する。
5. **P3運用足場**: Firestore rules test、小さなMode A eval、最小CI、API最小デプロイ手順が存在する。
6. **M2（P4）★**: `PUBLISHR_LLM=vertex`＋`DATA_SOURCE=firestore`＋`NEXT_PUBLIC_DATA_SOURCE=firestore` で `make dev`→ブラウザで観測→企画(revise)→棚5冊入荷、`map/`に却下→採用描画。API最小Cloud Runでもplanning手動トリガーが1回通る。
7. **M3（P5）**: M3a 手動1冊→M3b 予約API→M3c Pub/Sub worker→M3d Scheduler自律、の各段階で `read/[bookId]` で読める。
8. **M4（P6）**: push→Evalゲート（GEAP 8件・本命≥70）→自動デプロイ。<70でCI fail。
9. **新規テスト**: 各step output_schema妥当性／prompts loader全11本／mock決定性回帰／コストガード／Firestore rules／vertexは`@pytest.mark.vertex`。

## Open risks / 注意
- **P0aが最初の関門**（mock回帰が赤いままだと、以降の差分が安全に判定できない）。まず `make eval/verify/pipeline/smoke` を緑に戻す。
- **P0bがP2の前提**（schema/prompt/dispatcherなしでMiniLoopへ進むと使い捨て実装になる）。H0b未達ならP2停止。
- **P2 がプロジェクト全体の関門**（grounding+schema共存・state跨ぎrejectionFeedback・escalate脱出のランタイム実証）。詰まればSTEP2のみLangGraph。ただしH2を満たすまでP3へ進まない。
- **GCPコスト暴走**: Budget通知は検知であり停止ではない。Claude作業中の大量失敗/無限ループは、mock既定・dev実行縮小・実LLM上限・公開API認証/許可uid/連打防止で止める。Discord通知は見落とし防止として有効だが、主防御にしない。
- **scopeが大きい**（実質W1–W4相当・1.5人×5週）。P0a→P0b→P1→P2(H2) を最優先で通し、P3/P4で最小運用リスクを前倒し、P5はM3a〜M3dに分けて段階デプロイ。mock常時緑で「いつでも見せられる」状態を維持。
- **GCP齟齬**: P1冒頭の現状確認で実在を必ず突き合わせ、無いものだけ作る（二重作成・課金事故を防ぐ）。
- **役割整合**: WBS上 backend/基盤/DevOps=一瀬、フロント/プロンプト/Eval/デモ=鉄田。実LLM/GCP依存ステップはユーザー/一瀬の環境前提。
