# Pub/Sub planning worker 修正引き継ぎ

作成日: 2026-06-24 JST
確認ブランチ: `feat/3theme-restructure`
対象: Cloud Run `publishr-api` / GCP project `publishr-498123`

## 要約

実 Cloud Run / Firestore の縦通し確認は成立した。ただし、本番リスクのある不具合が見つかった。

- `POST /api/trigger/planning` は Pub/Sub planning job を正常に publish している。
- Pub/Sub は `/api/worker/plan` へ正常に push 配送している。
- planning worker は最終的に Firestore へ新規入荷を書き込めている。
- ただし、planning worker の処理時間が Pub/Sub push の HTTP 制限に近い、または超える。
- 約600秒を超えると Pub/Sub が同じ planning job を retry する。
- 生成される book ID に実行時刻 timestamp が入っているため retry が冪等にならない。
- 結果として、1回の trigger で 4冊バッチが複数回作られる。

主因は配送失敗ではなく、**長時間 push worker と冪等性不足**。

## 実環境確認の証拠

Cloud Run health:

```text
GET https://publishr-api-355143691286.asia-northeast1.run.app/api/healthz
=> {"status":"ok","dataSource":"firestore","llm":"vertex"}
```

trigger 前の Firestore:

```text
users=2
books=32
plans=4
personas=27
```

手動 trigger:

```text
POST /api/trigger/planning {"userId":"u_sakura"}
=> {"ok":true,"queued":true}
```

Cloud Run request log の時系列。時刻は UTC:

```text
2026-06-23T16:42:42Z POST /api/trigger/planning 200 latency=2.1s
2026-06-23T16:42:47Z POST /api/worker/plan      504 latency=599.99s
2026-06-23T16:53:01Z POST /api/worker/plan      504 latency=599.99s
2026-06-23T17:03:19Z POST /api/worker/plan      204 latency=492.27s
2026-06-23T17:01-17:16Z POST /api/worker/write  204 multiple times
```

待機後の Firestore:

```text
books=48
personas=40
```

追加された doc には複数の timestamp batch が含まれている。

```text
arr_20260624015650_*
arr_20260624020300_*
arr_20260624021129_*
arr_20260624060853_*
```

つまり、同じ論理 run の retry が同じ doc を上書きせず、別 batch として保存されている。

その他の warning:

```text
drive text extract failed ... mime=application/vnd.google-apps.folder ... fileNotExportable
Imagen 生成失敗 ... 429 RESOURCE_EXHAUSTED ... imagen-3.0-generate
```

これらは別途見る価値はあるが、今回の重複 batch の直接原因ではない。

## 現在の実環境設定

Cloud Run service:

```text
service=publishr-api
latestReadyRevision=publishr-api-00082-68x
DATA_SOURCE=firestore
PUBLISHR_LLM=vertex
QUEUE=pubsub
PUBLISHR_MAX_BOOKS_PER_RUN=4
ENABLE_IMAGEN=true
DEMO_UID=5JLLGOc3rpXiGN9KXmsISBNAKty2
PUBSUB_PLAN_PUSH_AUDIENCE=https://publishr-api-355143691286.asia-northeast1.run.app/api/worker/plan
PUBSUB_PUSH_AUDIENCE=https://publishr-api-355143691286.asia-northeast1.run.app/api/worker/write
```

Pub/Sub:

```text
topic=publishr-planning
subscription=publishr-planning-push
pushEndpoint=https://publishr-api-355143691286.asia-northeast1.run.app/api/worker/plan
ackDeadlineSeconds=600
retryPolicy=10s..60s
```

## まず見るべきコード

デプロイ済みの worker 実装は、現在の `feat/3theme-restructure` 作業ツリーより `origin/main` に近い。修正前に `origin/main` と比較すること。

最初に確認するファイル:

- `apps/api/publishr_api/routers/api.py`
- `apps/api/publishr_api/routers/worker.py`
- `apps/api/publishr_api/services/write_queue.py`
- `apps/api/publishr_api/services/pubsub_queue.py`
- `apps/api/publishr_api/services/mode_a_service.py`
- `agents/publishr_agents/persist_mapping.py`
- `infra/terraform/main.tf`

重要な現挙動:

- `api_trigger_planning` が `write_queue.enqueue_planning(...)` を呼ぶ。
- `enqueue_planning` が `{userId, owner, observeUid}` を `publishr-planning` に publish する。
- `/api/worker/plan` が Pub/Sub push HTTP リクエスト内で `mode_a_service.run(...)` を実行する。
- `mode_a_service.run(...)` は Google観測、Vertex planning/casting/preview/cover、arrivals永続化、per-book writing enqueue まで行う。
- `map_mode_a_to_books(...)` / persist 側が timestamp 付きの `arr_YYYYMMDDHHMMSS_*` ID を作るため、Pub/Sub retry が新規 book になる。

## 推奨修正

まず冪等性を入れる。timeout を伸ばすだけでは解決しない。

### 1. 安定した `runId` を追加

trigger 時点で安定した run ID を生成し、Pub/Sub payload に含める。

例:

```text
runId = planning_{ownerUid}_{YYYYMMDDHHMMSS}_{shortRandom}
```

Pub/Sub retry では payload が同一なので、`runId` も同一になる。

想定 touch point:

- `TriggerPlanningInput`
  - テストや手動検証用に optional `runId` を受けられると便利。
- `write_queue.enqueue_planning(...)`
- `pubsub_queue.publish_planning_job(...)`
- `worker.py` の `_planning_job_from_envelope(...)`
- `mode_a_service.run(..., run_id=...)`

### 2. Firestore に idempotency lock を追加

重い処理の前に server-owned な job doc を作る。

```text
planningJobs/{runId}
  ownerUid
  userId
  status: running | completed | failed
  createdAt
  startedAt
  completedAt
  bookIds[]
  errorType?
```

期待挙動:

- `status=completed` なら worker は即 `204`。
- `status=running` かつ十分新しいなら worker は即 `204`。
- doc がなければ transaction で作成し、その worker だけが処理を進める。
- 成功時は `completed` と `bookIds` を保存。
- 失敗時は `failed` と `errorType` を保存し、ログを出して、それでも `204` を返す。

Pub/Sub push は最初の試行中にも同じ message を再配送し得るので、「doc作成または既存running確認」は atomic にする。

### 3. book ID を run 単位で決定的にする

`datetime.now()` 由来の timestamp ではなく、`runId` を使って ID を作る。

```text
arr_{runId}_{slotOrPersonaId}
```

これにより lock をすり抜けた duplicate でも同じ doc を上書きできる。

主な touch point:

- `agents/publishr_agents/persist_mapping.py`
- `map_mode_a_to_books(...)`

### 4. 長時間処理の分離は次段階で検討

本筋の構成は以下。

- `/api/worker/plan` は認証・job登録だけ行い、すぐ ack する。
- 長い Vertex 実行は Cloud Run Jobs / Cloud Tasks / pull worker に逃がす。

ただしこれは変更範囲が大きい。まずは idempotency lock と deterministic ID で duplicate arrivals を止めるのが最小修正。

### 5. 短期運用回避

コード修正がデプロイされるまでの一時回避:

- `ENABLE_IMAGEN=false`
- または `PUBLISHR_MAX_BOOKS_PER_RUN=2`

600秒超過の確率は下がるが、retry や duplicate write の根本解決ではない。

## 推奨テスト

ユニット/契約テスト:

1. `enqueue_planning` が安定した `runId` を payload に入れる。
2. `_planning_job_from_envelope` が `runId` を parse できる。
3. 同じ `runId` の `worker_plan` を2回呼んでも `mode_a_service.run` は1回だけ。
4. `mode_a_service.run(..., run_id="fixed")` で決定的 book ID が作られる。
5. 同じ `runId` で persistence を繰り返しても book count が増えない。

ローカルの軽い統合テスト:

```powershell
$env:DATA_SOURCE='mock'
$env:QUEUE='mock'
uv run pytest apps/api/tests/test_api.py agents/tests/test_mode_a_set.py -q
```

既存の有用な確認:

```powershell
uv run pytest agents/tests/test_runtime_guard.py agents/tests/test_prompt_review_dump.py -q
npm.cmd --prefix apps/web run typecheck
npm.cmd --prefix apps/web run lint
```

デプロイ後の live verification:

1. Firestore の現在 book count を記録。
2. trigger を1回だけ実行。

```powershell
$body = @{ userId = 'u_sakura' } | ConvertTo-Json
Invoke-RestMethod `
  -Uri https://publishr-api-355143691286.asia-northeast1.run.app/api/trigger/planning `
  -Method Post `
  -ContentType 'application/json' `
  -Body $body `
  -TimeoutSec 120
```

3. Cloud Run logs で `/api/worker/plan` を確認。
4. 論理的に完了する `runId` が1つだけであることを確認。
5. Firestore の book 増加が最大4件であることを確認。
6. 制御されたテスト経路で同じ payload/runId を retry し、count が増えないことを確認。

## 読み取り専用の診断スニペット

Cloud Run request log:

```powershell
$env:UV_CACHE_DIR='C:\Users\ytets\publishr\.uv-cache'
@'
from __future__ import annotations
import json, urllib.request, datetime
import google.auth, google.auth.transport.requests

project='publishr-498123'
creds,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
creds.refresh(google.auth.transport.requests.Request())
now=datetime.datetime.now(datetime.timezone.utc)
start=(now-datetime.timedelta(hours=8)).isoformat().replace('+00:00','Z')
flt=f'''resource.type="cloud_run_revision"
resource.labels.service_name="publishr-api"
timestamp >= "{start}"
(httpRequest.requestUrl:"/api/worker/plan" OR httpRequest.requestUrl:"/api/worker/write" OR httpRequest.requestUrl:"/api/trigger/planning")'''
body=json.dumps({'resourceNames':[f'projects/{project}'],'filter':flt,'orderBy':'timestamp asc','pageSize':100}).encode()
req=urllib.request.Request('https://logging.googleapis.com/v2/entries:list',data=body,method='POST',headers={'Authorization':f'Bearer {creds.token}','Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=30) as r: data=json.loads(r.read().decode())
for e in data.get('entries',[]):
    h=e.get('httpRequest',{})
    print(json.dumps({
        'ts': e.get('timestamp'),
        'method': h.get('requestMethod'),
        'url': h.get('requestUrl'),
        'status': h.get('status'),
        'latency': h.get('latency'),
        'trace': e.get('trace','').rsplit('/',1)[-1],
    }, ensure_ascii=False))
'@ | uv run python -
```

Firestore inspection:

```powershell
$env:UV_CACHE_DIR='C:\Users\ytets\publishr\.uv-cache'
uv run python scripts\inspect_firestore.py
```

## Claude Code への注意

- mock 挙動は決定的に保つ。
- テストで実 GCP / Vertex 使用を増やさない。
- まず契約に効く小さな修正を優先する。
- live Cloud Run / Firestore 操作は手動ゲート扱いにする。
- 現在の worktree branch には、デプロイ済み worker code が全て入っていない可能性がある。編集前に `origin/main` と比較する。
