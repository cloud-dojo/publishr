"""Publishr BFF（FastAPI）アプリのエントリポイント。"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .errors import ConflictError, NotFoundError
from .routers import api, auth, books, personas, pipeline, plans, users, worker
from .services.rate_limit import RateLimitError

# 本番（Cloud Run）でアプリの INFO ログ（observe: 経路・trigger ok 等）を stdout へ出す。
# 未設定だと root 既定 WARNING で握りつぶされ、実観測/企画の切り分けができない（#6）。
# LOG_LEVEL で上書き可（既定 INFO）。uvicorn のアクセスログとは別系統。
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Publishr BFF", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
async def _not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": exc.message})


@app.exception_handler(ConflictError)
async def _conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"error": exc.message})


@app.exception_handler(RateLimitError)
async def _rate_limit_handler(_request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"error": exc.message})


def _health() -> dict:
    return {"status": "ok", "dataSource": settings.data_source, "llm": settings.publishr_llm}


@app.get("/healthz", tags=["meta"])
def healthz() -> dict:
    # ローカル用。注意: `*.run.app` の Google エッジは `/healthz` を予約パスとして横取りし
    # コンテナに届かない（公開URLでは 404）。Cloud Run/外形監視は `/api/healthz` を使う。
    return _health()


@app.get("/api/healthz", tags=["meta"])
def api_healthz() -> dict:
    """Cloud Run/公開URL から到達可能な health（`/healthz` はエッジ予約で届かないため）。"""
    return _health()


for _router in (
    books.router,
    plans.router,
    personas.router,
    users.router,
    pipeline.router,
    api.router,
    auth.router,
    worker.router,
):
    app.include_router(_router)
