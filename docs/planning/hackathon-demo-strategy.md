# ハッカソン提出・審査デモ方針（無認証公開＋ライブ生成のキャップ運用）

> 作成: 2026-06-28 ／ 最終更新: 2026-07-01 ／ 対象: DevOps × AI Agent Hackathon（Findy）提出〜審査
> 結論: **「無認証の公開ショーケース（佐倉）＋ 匿名でも押せるライブ生成ボタン（厳格にキャップ）」**。
> OAuthはTestingのまま。審査員に自分のGoogle連携はさせない。コストは多層キャップ＋Cloud Billingで$50前後に固定。

> **実装現状（2026-07-01）**: PR #96（無認証ショーケース）・#97（レートガード）ともに **main マージ・本番デプロイ済み**。
> - ✅ **稼働中**: 無認証の読み取り専用ショーケース。審査員はログイン無しで佐倉の書店 / 3企画(reject_log) / 入荷理由を閲覧・読書できる（実機で 200 / CORS許可 / bffビルド反映 / BFFデータ 佐倉published 20冊 を確認）。
> - 😴 **dormant（コード反映済・未点火）**: ライブ生成ボタン＋日次レートガード。`NEXT_PUBLIC_DEMO_LIVE_GEN` 未設定＋caps=0＝**ボタン非表示・レート無効＝晒されない**。デモ当日に env で点火する。
> - **1冊化**: `PUBLISHR_SET_MAX_BOOKS` キルスイッチ実装済（既定=全冊・非破壊／点火時 `=1`）。
> - **残タスク**: C（/connect導線外し）／F（締切前の佐倉プール生成）／ブラウザ目視確認／当日の env 点火＋通しテスト。
>
> **点火チェックリスト（デモ当日・全部同時に）**: `web: NEXT_PUBLIC_DEMO_LIVE_GEN=1` ／ `Cloud Run: PUBLISHR_DEMO_RATE_GLOBAL_CAP=7 / PUBLISHR_DEMO_RATE_PER_CLIENT_CAP=3 / PUBLISHR_SET_MAX_BOOKS=1` ／ `GCP: Cloud Billing 予算上限` ／ `Scheduler: honmei/serendipity 一時停止`。
>
> 環境: web=`publishr--publishr-498123.asia-east1.hosted.app`（App Hosting・`NEXT_PUBLIC_DATA_SOURCE=bff`）／ BFF=`publishr-api`(asia-northeast1)／ demo_uid=`5JLLGOc3rpXiGN9KXmsISBNAKty2`（佐倉）。関連コード: `services/demo_rate_limit.py`・`data/config.ts`(DEMO_OWNER_UID / getDemoClientId / demoLiveGenEnabled)・`account/page.tsx`・`mode_a.py`(max_books)。

---

## 0. TL;DR（最終方針＝②ライブ生成公開）

- デモは**無認証**。審査員含め誰でも、**佐倉美咲アカウントのページを既定表示**で閲覧できる。パスワードなし（→ **I-32 ID/Password認証はクローズ**）。
- 既定ビューは **BFF経由で佐倉(demo_uid)の published を無ログイン表示**（PR-A実装済）。見せ場の片方＝**実際の読書ページ体験**。
- もう片方の見せ場＝**「今すぐ企画」ボタンを匿名にも開放し、押下で実Vertexのライブ生成が走る様子**（3企画AIの視点差→却下→再提出→入荷）を見せる。審査基準①「AIエージェントである必然性・自律的な判断/タスク実行」に直撃。
- ただしライブ生成は**実課金**なので**多層キャップ必須**: 1回1冊（devプロファイル）・**グローバル日次7**・per-anon 3/日・per-run ¥100・**Cloud Billing $50停止**。
- 公開は**約2週間（審査期間）限定**。期間を区切るので合計上限は不要、Cloud Billingが最終天井。
- OAuth同意画面は **Testingのまま**（審査員は自分のGoogleを連携しない＝restricted scope審査もプライバシー障壁も回避）。佐倉の観測トークンは7日失効するので**期間中1回は再認証**して接地を保つ（or 後半はfixture接地で割り切る）。

> **方針の変遷（記録）**: 初期は「事前生成を凍結→キャンド入荷（課金ゼロ）」案だった（旧§4・旧item E）。
> 2026-06-30 に **②ライブ生成公開（capped）へ転換**。理由＝審査員に「実エージェントが動く様子」を体験させる価値が、
> 凍結の安全性を上回ると判断。安全性は**キャップ＋Cloud Billing＋2週間限定**で担保する。

---

## 1. 提出・審査タイムライン

| 日程 | 内容 | デモ的含意 |
|---|---|---|
| **2026-07-10(金) 23:59** | 提出締切（GitHub公開URL・デプロイURL・ProtoPedia） | リポは**公開必須**。デプロイURLは動作確認される |
| 2026-07-13〜07-17 | 一次審査（運営事務局） | 審査員がデプロイURLを**無人で開いて動作確認** |
| 2026-07-21〜07-24 | 二次審査（外部有識者） | 同上・無人 |
| 2026-07-30(木) | 受賞者・決勝進出者発表 | — |
| 2026-08-19(水) | 最終発表＠Google渋谷（上位10チームのみ） | **ここだけ有人ライブ** |

- 「デプロイURLは審査時に動作確認を行います。締切以降も一定期間アクセス可能な状態を維持してください。」
  → **少なくとも 7/24 までデプロイを無傷で維持**。ライブ生成ボタンを開けるのは**この約2週間に限定**する。

---

## 2. 背景インシデント: OAuth 7日失効 → デモ垢が空観測に縮退

### 2.1 何が起きたか

デモ垢（`demo_uid = 5JLLGOc3rpXiGN9KXmsISBNAKty2`／佐倉 美咲・publishr.hackathon）のSTEP0観測が、
本番で **実Google観測 → fixtureフォールバック → 空の観測束** に縮退し、デモ固定日付（`_DEMO_NOW = 2026-06-03`）で
本生成していた。

縮退の連鎖:

1. OAuth同意画面が **External × Testing** のため、refresh_token が **発行から7日で失効**（Google仕様）。
2. `mode_a_service._observation_source()` の `except` が `RefreshError` を握りつぶし、**`FixtureObservationSource` へ縮退**。
3. fixture はこの実uid `5JLLGOc3...` のディレクトリを持たない（あるのは `u_mita`・`u_sakura`）→ `_load_persona` が `{}` → **空の観測束**。
4. fixture経路なので観測アンカーが `_DEMO_NOW`(2026-06-03) に固定 → 「collectedAt が古い」現象。
5. 加えて当該垢は `initialProfile.skipped: true`（オンボ未完）で base 素材も空。

### 2.2 失効タイミング（7日パターンの実証）

| トークン version | 発行 | 失効（発行+7日） | 観測 |
|---|---|---|---|
| v5 | 2026-06-17 | 〜2026-06-24 | 6/24まで成功 → 6/26,6/27の定期runで `RefreshError` |
| v6 | 2026-06-28 | **〜2026-07-05見込み** | 再認証で復活 |

→ **連携自体は健全。問題は「Testingの7日失効」だけ**。ライブ生成を期間中通すなら、**約7日ごとに再認証**して佐倉の実接地を保つ。

---

## 3. `/connect` 画面の誤表示（別バグ・同根）

- 症状: 再認証後の `/connect?connected=1` が「連携完了」と出しつつ、Drive/Calendar を「未連携」、Tasks のみ「連携済み」と表示。
- 真因: **フロントとバックエンドでデモuidが食い違っている**。
  - フロント表示: `DEMO_USER_ID = "u_sakura"`（`apps/web/src/data/config.ts:51`）
  - バックエンド実体: `demo_uid = "5JLLGOc3..."`（観測・トークン・trigger はこちら）
- 結論: **表示バグであり、実際は3つとも連携済み**。無認証ショーケースでは `/connect` 自体を導線から外すのが素直。

---

## 4. 最終方針: ②無認証公開＋ライブ生成（capped）

### 4.1 体験フロー

1. 審査員がデプロイURLを開く → **ログイン不要で佐倉の書店**（既定表示）。本を開いて**読書体験**。
2. 「今すぐ企画」ボタン（`account`）を押す → **実Vertexのライブ生成**が走る → 数分で佐倉の棚に新刊が入荷。
   観測→読者→**3企画AIの視点差→リーダー却下→再提出→採用(reject_log)→入荷理由** が見える。

### 4.2 採用モデル: (2a) 佐倉の共有棚にライブ生成

- 匿名が押した生成も **owner=佐倉(demo_uid)・佐倉の実Google観測で走る**（＝映える・実装も軽い）。
- 匿名IDは「**回数キャップの単位としてだけ**」使う（生成の所有や観測には使わない）。
- ＝「今の企画ボタンを匿名に開放し、匿名ごとに上限をかける」。全員が同じ佐倉棚を見る。

### 4.3 OAuth同意画面は Testing のまま

- 審査員は**自分のGoogleを連携しない**ので、restricted scope（`drive.readonly`）のCASA審査も「未確認アプリ」警告もプライバシー障壁も**回避**。
- 連携しているのは**佐倉だけ**。佐倉トークンの7日失効には**期間中の再認証**で対処（§2.2）。

---

## 5. コスト & キャップ（②の安全弁）

### 5.1 1生成あたり（devプロファイル＝1冊・1,500字・Imagen無・編集1R）

モデル単価（`agents/publishr_agents/llm/runtime.py:71` 自前定数）:
- **pro**(gemini-2.5-pro): ¥350/¥1,050 per Mtoken（入/出）
- **flash**(gemini-2.5-flash): ¥50/¥200 per Mtoken

devプロファイルの per-run 上限は **¥100**（`max_estimated_cost_jpy`）。1冊デモ規模の実費は **≈ ¥50〜100（$0.35〜0.65）**。
（prodプロファイル＝4冊・12,000字・Imagen有・編集3R は per-run ¥2,000≈$13。**デモには使わない**。）

### 5.2 日次キャップ → 2週間コスト

| グローバル日次 | 1日 | 審査2週間(14日) |
|---|---|---|
| **7/日（採用）** | ~¥350〜700（**$2〜5**） | **~¥5,000〜10,000（$33〜65）** |
| 50/日 | ~¥5,000（$33） | ~¥70,000（$460）← 不採用 |

### 5.3 採用キャップ（多層）

| ガード | 値 | 役割 | 実装/操作 |
|---|---|---|---|
| 生成規模 | **devプロファイル固定**（1冊・1,500字・Imagen無・編集1R） | 1生成 ~¥50-100 に固定 | BFF：デモtriggerはdevプロファイル強制 |
| per-run 上限 | **¥100**（既存 `max_estimated_cost_jpy`） | 1回が暴走しない | 既存ガード流用 |
| **グローバル日次** | **7/日** | 全匿名合計のペース天井 | BFF：新規レートガード |
| per-anon | **3/日・人**（client-id基準・回避可は承知） | 善意の連打抑制（ソフト） | BFF＋フロントでclient-id |
| 公開期間 | **約2週間限定**（≈7/10–7/24） | 期間を区切る＝合計上限不要 | 運用（ボタン/デプロイ開閉） |
| **Cloud Billing** | **$50で停止/アラート** | 最終天井（何が起きてもここで止まる） | あなたがGCPで設定 |

→ **想定総額 $33〜65、最悪でも Cloud Billing $50 で頭打ち**。

---

## 6. アクション項目

### 6.1 コード（担当: 一瀬）

| # | 内容 | 対象 | 状態 |
|---|---|---|---|
| A | **ショーケース公開棚化（=DATA_SOURCE=bff切替）** — 既定を bff-provider（無認証・佐倉owner絞り済み）に、`AuthGuard` の `/login` 誘導をbffで停止 | `apphosting.yaml`×2・`AuthGuard.tsx` | 🟡 実装済（branch `feat/bff-public-showcase`・tsc緑） |
| B | **uid不整合の是正** — bff-provider の `/users/u_sakura` と実owner `5JLLGOc3` のズレ（挨拶/profile）。表示ユーザーを佐倉に寄せる | `bff-provider.ts:39`・`config.ts:51` | ⬜ 次サブタスク |
| C | **`/connect` 導線外し**（無認証では連携UI不要） | `ConnectSources.tsx` / `(auth)/connect` | ⬜ 未着手 |
| **②G** | **ライブ生成のキャップ実装（本丸）** — `/api/trigger/planning`（or 専用デモtrigger）前段に **グローバル日次7＋per-anon3（client-id）** レートガードを新設（TDD・`TriggerGuard`拡張）。**devプロファイル強制**（1冊・短文・Imagen無）。owner=佐倉固定、actor=client-idで計数。上限到達は429→UIで「本日の体験枠は終了」 | 新規 BFFガード・`config.ts` `canManualTrigger`緩和・`account/page.tsx:376-405`・`bff-provider.ts` | ⬜ 未着手 |

> **旧item E（キャンド入荷・課金ゼロ）は②採用により取り下げ**。実Vertexのライブ生成を見せる方針に変更（§0変遷）。
> `今すぐ企画`の実Vertex経路（`runPipeline`→`/api/trigger/planning`）を**活かす**側に転換した。

### 6.2 運用（担当: 一瀬）

| # | 内容 | 状態 |
|---|---|---|
| OAuth | **同意画面はTesting放置**（本番化/CASA審査不要） | ✅ 方針確定 |
| Billing | **Cloud Billing 予算 $50 で停止/アラート**（②の最終天井・最優先の運用ガード） | ⬜ 未設定（要GCP操作） |
| 再認証 | 佐倉トークンを**期間中~7日ごとに再認証**（ライブ生成の実接地維持）。後半fixture接地で割り切るなら省略可 | ⬜ 運用 |
| Scheduler | `honmei`/`serendipity` はボタン外で佐倉棚に生成＝**キャップ外コスト＋失効後の汚染源**。**公開期間は一時停止**を推奨 | ⬜ 7/10前に判断 |
| F | **締切前に佐倉で良質な接地データを生成**（既定表示＋読書体験の初期コンテンツ）→ キュレーション | ⬜ 未着手 |
| 開閉 | ライブ生成（ボタン/デプロイ）を**約2週間だけオープン**。審査終了後はボタン無効化 or デプロイ縮退 | ⬜ 運用 |
| G | **リポ公開のためのシークレット/PII掃除**（提出は公開リポ必須） | ⬜ 別途 |
| H | **デプロイURLの維持**（少なくとも 7/24 まで無傷稼働） | ⬜ 継続 |

---

## 7. 参照（環境・コマンド）

- プロジェクト: `publishr-498123` ／ region `asia-northeast1` ／ Cloud Run service `publishr-api`
- Web: `https://publishr--publishr-498123.asia-east1.hosted.app`（Firebase App Hosting・`apphosting.yaml`）
- デモ垢: `demo_uid = 5JLLGOc3rpXiGN9KXmsISBNAKty2`（佐倉 美咲 / publishr.hackathon）
- OAuthトークン: Secret Manager `google-oauth-5JLLGOc3rpXiGN9KXmsISBNAKty2-e14093ef231a`
- モデル/コスト定数: `agents/publishr_agents/llm/runtime.py`（`_MODEL_COST_JPY_PER_MTOKEN` / `_DEV_DEFAULTS` / `_PROD_DEFAULTS`）
- 既存トリガー: `POST /api/trigger/planning`（`account/page.tsx` の「今すぐ企画」／Scheduler）

再認証確認（新versionが入ったか・値は読まない）:
```
gcloud secrets versions list google-oauth-5JLLGOc3rpXiGN9KXmsISBNAKty2-e14093ef231a \
  --project=publishr-498123 --format='table(name,state,createTime)'
```

観測フォールバック分岐の確認:
```
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="publishr-api" AND textPayload:"observe:"' \
  --project=publishr-498123 --limit=10 --freshness=2d --format='value(timestamp, textPayload)'
```
