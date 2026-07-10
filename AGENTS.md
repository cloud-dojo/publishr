# Publishr Agent Guidance

## Core Rules

設計/MVPスコープと、作業分解・実装順序・ハードゲートの正本（WBS）は、公開リポジトリには含めず非公開（repo外）で管理している。公開リポジトリ上ではこの `AGENTS.md` / `CLAUDE.md` の Core Rules を正本として扱う（`docs/` 配下の設計・計画ドキュメントはリポジトリに存在しない）。

- 最優先はC0.1: `make verify`、`make eval`、`make pipeline`、`make smoke` を緑に戻すこと。赤い間は他の実装を広げない。
- C0.2まではmock挙動差分ゼロを守る。v2 schema、prompt loader、LLM dispatcherは追加してよいが、`PUBLISHR_LLM=mock` の導線を壊さない。
- C1.0.1未達ではC1.1以降の本格実装に進まない。MiniLoopの実Vertex検証、`escalate`脱出、再実行CLI、成功JSON、vertex最小テストを揃えてから次へ進む。
- ユーザーが明示しない限り、通常作業はオフラインかつ決定的に保つ。実LLM/GCPはB1.3/C1.0.1のゲート作業として隔離する。
- 証拠になる要素を守る: 企画3体の異なる視点、`reject_log` の却下/再提出証跡、書店UIで見える入荷理由。
- 広いリファクタより、デモ導線を壊さない小さな変更を優先する。
- フロント/バックエンド契約を変える場合は、`packages/shared-schema/`、fixtures、pydanticモデル、API利用側を一緒に更新するか、影響を明示する。

## Python / ADK Rules

- BFFのデータアクセスは `RepositoryProtocol` の内側に置く。MVPの既定実装は `MockRepository`。
- C0.1中は `scripts/eval_harness.py` と `eval/eval_set.yaml` の整合を最優先し、`make eval` と `make verify` を緑に戻す。
- C0.2中は `agent_io.py`、state keys、prompt loader/registry/render、LLM provider、`PUBLISHR_LLM` dispatcherを追加してよいが、mock時の既存挙動を変えない。
- タスクがC1.0.1の実LLM連携を明示しない限り、エージェント出力は決定的なキャンド出力にする。
- パイプライン状態は `observe -> reader -> planning -> selection_gate -> author_agenda -> cover` が追える形で保持する。
- C1.0.1ではMiniLoopの実Vertexランタイム検証を使い捨てにしない。再実行CLI、成功JSON、`@pytest.mark.vertex` 最小テストを残す。
- テストは実装詳細より先に、契約の挙動、リポジトリ状態遷移、パイプライン出力形状を押さえる。
- pytestコマンドはルートの `pyproject.toml` と `make verify` に合う状態を保つ。
- ローカルMVPのコードパスにクラウド依存を混ぜない。必要な場合は `DATA_SOURCE` や `PUBLISHR_LLM` などの切替の奥に隔離する。
