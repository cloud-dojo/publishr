"""Publishr BFF（FastAPI）アプリのエントリポイント。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .errors import ConflictError, NotFoundError
from .routers import api, books, personas, pipeline, plans, users

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


for _router in (books.router, plans.router, personas.router, users.router, pipeline.router, api.router):
    app.include_router(_router)
