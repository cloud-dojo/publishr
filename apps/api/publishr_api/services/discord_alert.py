"""Cloud Monitoring インシデント → Discord webhook 中継（本文未承認published アラートの能動通知）。

GCP の webhook 通知チャネルが送るインシデントJSONを Discord の `{"content": ...}` 形式に整形して
POST する。ネットワーク送信は stdlib（urllib）のみ＝新規 runtime 依存なし。best-effort（失敗は
warning ログのみ）で、呼び出し側（endpoint）は常に 2xx を返し GCP の再送ストームを避ける。
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# Discord のメッセージ content 上限（超過は 400）。安全側に丸める。
_DISCORD_CONTENT_LIMIT = 2000


def format_discord_content(incident: dict[str, Any]) -> str:
    """GCP インシデント（payload["incident"]）を Discord メッセージ本文へ整形する。

    欠損キーがあっても例外を出さず文字列を返す（防御的）。上限 2000 文字に丸める。
    """
    policy = incident.get("policy_name") or "(policy 不明)"
    state = incident.get("state") or "unknown"
    condition = incident.get("condition_name") or ""
    summary = incident.get("summary") or ""
    url = incident.get("url") or ""

    lines = [f"🚨 **[Publishr Monitoring] {policy}**", f"state: `{state}`"]
    if condition:
        lines.append(f"condition: {condition}")
    if summary:
        lines.append(f"> {summary}")
    if url:
        lines.append(url)
    content = "\n".join(lines)

    if len(content) > _DISCORD_CONTENT_LIMIT:
        content = content[: _DISCORD_CONTENT_LIMIT - 3] + "..."
    return content


def post_to_discord(webhook_url: str, content: str) -> bool:
    """Discord webhook へ content を POST する（best-effort・stdlib のみ）。成否を返す。"""
    data = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 — 送信先は運用が設定する Discord webhook（固定スキーム）
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            ok = 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001 — 通知転送の失敗は致命でない（ログのみ）
        logger.warning("discord relay failed: %s", type(exc).__name__)
        return False
    if not ok:
        logger.warning("discord relay non-2xx: %s", resp.status)
    return ok


def relay_incident(webhook_url: str, payload: dict[str, Any]) -> bool:
    """payload["incident"] を整形して Discord へ送る。incident 欠落時は False（送信せず）。"""
    incident = payload.get("incident") if isinstance(payload, dict) else None
    if not isinstance(incident, dict):
        logger.warning("monitoring: payload に incident が無い、skip")
        return False
    return post_to_discord(webhook_url, format_discord_content(incident))
