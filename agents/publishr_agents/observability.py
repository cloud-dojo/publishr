"""Langfuse best-effort 計装（P2）。

langfuse 未インストール／キー未設定なら **no-op**（MiniLoop本体は計装に依存しない）。
LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST を env から読む。
"""

from __future__ import annotations

import os
from typing import Any, Optional


def _client():
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import Langfuse  # type: ignore
    except Exception:
        return None
    try:
        return Langfuse()  # LANGFUSE_* env から設定を読む
    except Exception:
        return None


def trace_miniloop(result: dict[str, Any]) -> str:
    """MiniLoop の1run（観測根拠・各R score/decision・採否）を1トレースで送る。

    戻り値は人間向けステータス文字列（"sent" / "skipped..." / "error..."）。
    """
    lf = _client()
    if lf is None:
        return "skipped (langfuse未導入 or LANGFUSE_*キー未設定)"
    try:
        history = result.get("verdict_history", [])
        root = lf.start_span(
            name="publishr-miniloop",
            input={"theme": result.get("theme")},
            metadata={
                "rounds": result.get("rounds"),
                "forcedApprove": result.get("forced_approve"),
                "verdictHistory": history,
                "subMarket": (result.get("subMarket") or "")[:2000],
                "approved": bool(result.get("approvedPlan")),
            },
        )
        # 各ラウンドを子スパンで（却下→再提出→採用の遷移を可視化）
        for v in history:
            child = root.start_span(name=f"round_{v.get('round')}", metadata=v)
            child.end()
        root.update(output={"approved": bool(result.get("approvedPlan"))})
        root.end()
        lf.flush()
        return "sent"
    except Exception as e:  # 計装失敗は致命ではない
        return f"error: {type(e).__name__}: {e}"
