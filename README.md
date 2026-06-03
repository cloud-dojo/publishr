# Publishr

> **あなた専属の、AI出版社。**
> あなたのメモ（Google Keep想定）を自律的に観測し、編集部AIが企画会議を開いて本を企画し、あなたの「書店」に並べる。気になる一冊を選ぶと、専属の作家AIが書き下ろす。

これは **ローカルで動くMVP** です。GCP/デプロイ/CI/CD はまだ含みません（将来）。観測ソースはモックの Keep メモ、エージェントのLLMは決定的なキャンド出力（オフライン）です。

## 一まわりの体験（ローカルE2E）

```
Keep観測 → 読者分析 → 企画会議(3体の企画AI → 企画リーダーが選抜 / 却下→再提出)
        → 著者アジェンダ生成 → 装丁 → 「書店」に入荷(draft)
        → ユーザーが予約 → 執筆 → published → 読書 → フィードバック
```

「却下→再提出」のログ（`reject_log`）が、単一生成では出せない**多様性→選抜**の証拠になります（基準1）。

## 構成（モノレポ）

```
apps/web/                Next.js 書店UI（App Router + TS + Tailwind + shadcn/ui）
apps/api/                FastAPI BFF（リポジトリ抽象 + パイプライン起動）
agents/publishr_agents/  ADK マルチエージェント（企画会議パイプライン）
packages/shared-schema/  契約: fixtures(JSON) + TS型 + Pythonモデル
packages/prompts/        作家ペルソナ・企画/著者プロンプト
docs/planning/           企画ドキュメント（アーキ・ピッチ・デモ台本）
docs/mockup/             デザインの正典（HTML/CSSモックアップ）
docs/IMPLEMENTATION_PLAN.md  実装プラン
```

## ローカル起動

```bash
make setup            # uv(Python3.12) + npm 依存をインストール
make api              # ターミナル1: BFF  → http://localhost:8000/docs
make web              # ターミナル2: 書店UI → http://localhost:3000
```

データ取得元は `apps/web/.env.local` の `NEXT_PUBLIC_DATA_SOURCE` で切替:
- `bff`（既定）: FastAPI 経由
- `mock`: フロント単独（API不要・デモ安全網）

```bash
make pipeline         # 企画パイプライン単体をオフライン実行（reject_log を確認）
make eval             # eval/eval_set.yaml の観点を決定的パイプラインで判定
make verify           # pytest + web lint/typecheck
```

## 将来（このMVPの先）

- 実Firestore / Cloud Storage 接続（`DATA_SOURCE=firestore`）
- Vertex AI Gemini 接続（`PUBLISHR_LLM=vertex`）
- Cloud Run デプロイ + Cloud Scheduler/Pub-Sub + GitHub Actions CI/CD（Evalゲート）
- Google Keep 実連携（※個人アカウントは公開API制約あり。Takeout/エクスポート等を検討）
