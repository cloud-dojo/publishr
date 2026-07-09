# Publishr — ローカルMVP用タスク
# 前提: node>=22, uv>=0.10 （Python 3.12 は uv が用意）

.PHONY: help setup setup-py setup-web web api pipeline dev smoke eval eval-gate eval-gate-vertex eval-repro eval-sweep verify test-py lint-web typecheck-web fmt

help:
	@echo "make setup     - Python(uv) と Web(npm) の依存をインストール"
	@echo "make api       - FastAPI BFF を起動 (http://localhost:8000)"
	@echo "make web       - Next.js フロントを起動 (http://localhost:3000)"
	@echo "make dev       - API と Web を1コマンドで起動（既存起動中なら再利用）"
	@echo "make smoke     - ローカルE2Eを1コマンドでスモーク確認"
	@echo "make pipeline  - ADK企画パイプラインをオフライン実行"
	@echo "make eval      - Eval観点をオフライン判定"
	@echo "make eval-gate - Eval judge 品質ゲート（mock・cases 7/8・未満で exit 1）"
	@echo "make eval-gate-vertex - 同ゲートを実 Gemini Pro judge で（課金・要 ADC/Vertex）"
	@echo "make eval-repro- judge再現性（複数回採点のσ/CV/一致・C5.4）"
	@echo "make eval-sweep- 閾値感度スイープ（本命合格ラインを振る・C5.5）"
	@echo "make verify    - pytest + web lint/typecheck"

setup: setup-py setup-web

setup-py:
	uv sync --all-packages --all-extras --dev

setup-web:
	npm install
	npm --prefix apps/web install

api:
	uv run uvicorn publishr_api.main:app --reload --port 8000

web:
	npm --prefix apps/web run dev

pipeline:
	uv run python -m publishr_agents.run_pipeline --user u_tadokoro

dev:
	uv run python scripts/local_dev.py

smoke:
	uv run python scripts/local_smoke.py

eval:
	uv run python -m scripts.eval_harness

eval-gate:
	uv run python -m scripts.eval_gate

eval-gate-vertex:
	uv run --with truststore python -m scripts.eval_gate --backend vertex

eval-repro:
	uv run python -m scripts.eval_reproducibility

eval-sweep:
	uv run python -m scripts.eval_threshold_sweep

verify: test-py lint-web typecheck-web

test-py:
	uv run pytest

lint-web:
	npm --prefix apps/web run lint

typecheck-web:
	npm --prefix apps/web run typecheck
