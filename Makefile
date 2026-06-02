# Publishr — ローカルMVP用タスク
# 前提: node>=22, uv>=0.10 （Python 3.12 は uv が用意）

.PHONY: help setup setup-py setup-web web api pipeline dev verify test-py lint-web typecheck-web fmt

help:
	@echo "make setup     - Python(uv) と Web(npm) の依存をインストール"
	@echo "make api       - FastAPI BFF を起動 (http://localhost:8000)"
	@echo "make web       - Next.js フロントを起動 (http://localhost:3000)"
	@echo "make pipeline  - ADK企画パイプラインをオフライン実行"
	@echo "make verify    - pytest + web lint/typecheck"

setup: setup-py setup-web

setup-py:
	uv sync

setup-web:
	npm install

api:
	uv run uvicorn publishr_api.main:app --reload --port 8000

web:
	npm --workspace apps/web run dev

pipeline:
	uv run python -m publishr_agents.run_pipeline --user u_tadokoro

dev:
	@echo "別々のターミナルで 'make api' と 'make web' を起動してください"
	@echo "  API: http://localhost:8000/docs   Web: http://localhost:3000"

verify: test-py lint-web typecheck-web

test-py:
	uv run pytest

lint-web:
	npm --workspace apps/web run lint

typecheck-web:
	npm --workspace apps/web run typecheck
