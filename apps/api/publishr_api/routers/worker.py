"""Pub/Sub push を受ける執筆ワーカー endpoint（C2.2 Phase②）。

`POST /api/worker/write` に Pub/Sub の push エンベロープ（{message:{data:base64(json{bookId})}}）が届く。
冪等に `process_write_job` を呼び、必ず 2xx を返して ack する（不正/欠損メッセージも ack＝再配信ループ防止）。

公開サービス（--allow-unauthenticated）上に置くため、`PUBSUB_PUSH_AUDIENCE` が設定されている時は
**push の OIDC トークンを自前検証**（audience＝worker URL・許可 push SA 一致）して不正 POST を弾く。
未設定（ローカル/mock）では検証スキップ＝オフラインでテスト可能。
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool

from ..config import settings
from ..deps import get_repository
from ..repositories.protocol import RepositoryProtocol
from ..services import reservation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["worker"])


def _verify_push(request: Request) -> None:
    """Pub/Sub push の OIDC を検証（audience 設定時のみ＝本番）。失敗は 401/403。"""
    audience = settings.pubsub_push_audience
    if not audience:
        return  # ローカル/mock: 検証スキップ
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth[7:]
    try:
        from google.auth.transport import requests as g_requests  # noqa: PLC0415
        from google.oauth2 import id_token  # noqa: PLC0415

        claims = id_token.verify_oauth2_token(token, g_requests.Request(), audience)
    except Exception as exc:  # noqa: BLE001 — 検証失敗は 401（理由はログのみ）
        logger.warning("push OIDC verify failed: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="invalid push token") from exc
    if settings.pubsub_push_sa and claims.get("email") != settings.pubsub_push_sa:
        raise HTTPException(status_code=403, detail="unauthorized push service account")


def _book_id_from_envelope(envelope: dict[str, Any]) -> str | None:
    data_b64 = (envelope.get("message") or {}).get("data")
    if not data_b64:
        return None
    try:
        payload = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception:  # noqa: BLE001 — 壊れたメッセージは ack して捨てる
        return None
    book_id = payload.get("bookId")
    return str(book_id) if book_id else None


@router.post("/worker/write")
async def worker_write(
    request: Request, repo: RepositoryProtocol = Depends(get_repository)
) -> Response:
    """予約された本を執筆して published にする（冪等）。常に 2xx で ack する。"""
    _verify_push(request)
    try:
        envelope = await request.json()
    except Exception:  # noqa: BLE001
        envelope = {}
    book_id = _book_id_from_envelope(envelope if isinstance(envelope, dict) else {})
    if not book_id:
        logger.warning("worker: bad/empty message, acking")
        return Response(status_code=204)  # ack（再配信ループ防止）
    # threadpool で実行＝同期 process_write_job が内部で asyncio.run（vertex本文生成）を呼んでも
    # 実行中イベントループとネストしない（C2.2/実Vertex対応）。mock経路はそのまま高速。
    await run_in_threadpool(reservation_service.process_write_job, repo, book_id)  # 冪等
    return Response(status_code=204)
