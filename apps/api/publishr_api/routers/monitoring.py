"""Cloud Monitoring の webhook 通知チャネルを受ける中継 endpoint。

`POST /api/monitoring/discord-alert` に GCP がインシデントJSONを push する。それを Discord webhook へ
整形転送する（本文未承認published アラートの能動通知・レベル1続き）。

公開サービス（--allow-unauthenticated）上に置くため、`PUBLISHR_MONITORING_WEBHOOK_TOKEN` 設定時は
GCP チャネルURLの `?token=` を照合して不正 POST を弾く（webhook はOIDCが無いのでURL埋め込みトークンで
保護）。未設定（ローカル/mock）は検証スキップ＝オフラインでテスト可能。`PUBLISHR_DISCORD_ALERT_WEBHOOK_URL`
未設定なら no-op で 2xx＝外部送信ゼロ・既存挙動不変。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from ..config import settings
from ..services import discord_alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.post("/monitoring/discord-alert")
async def discord_alert_relay(request: Request) -> Response:
    """GCP インシデントを Discord へ中継。常に 2xx で受け流し（再送ストーム防止）、不正トークンのみ 401。"""
    # URL 埋め込みトークン検証（設定時のみ＝本番。worker の audience 空スキップと同方針）。
    if settings.monitoring_webhook_token:
        if request.query_params.get("token") != settings.monitoring_webhook_token:
            logger.warning("monitoring: bad/missing token, rejecting")
            raise HTTPException(status_code=401, detail="invalid token")

    # Discord 未設定（ローカル/mock 既定）＝外部送信せず受け流す（挙動不変）。
    if not settings.discord_alert_webhook_url:
        return Response(status_code=204)

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 — 壊れた body でも ack（GCP の再送ストーム防止）
        payload = {}

    discord_alert.relay_incident(
        settings.discord_alert_webhook_url, payload if isinstance(payload, dict) else {}
    )
    return Response(status_code=204)
