"""Langfuse best-effort 計装（P2 / C5.6）。

langfuse 未インストール／キー未設定なら **no-op**（本体は計装に依存しない）。
LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST を env から読む。

C5.6: 「AIの必然性」の証跡＝2つの差し戻しループ（①企画リーダー / ②編集長の本文）と
grounding 取得URL を 1 トレースで可視化する（`trace_pipeline`）。
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


def grounding_urls_from_events(events: Any) -> list[str]:
    """ADK イベント列から grounding(google_search) の取得元URLを抽出する。

    `event.grounding_metadata.grounding_chunks[].web.uri` を防御的に拾い、重複除去・順序保持で返す。
    形が違う/未grounding なら空（計装は best-effort）。「検索URL」可視化(C5.6)の素材。
    """
    urls: list[str] = []
    for ev in events or []:
        meta = getattr(ev, "grounding_metadata", None)
        chunks = getattr(meta, "grounding_chunks", None) or []
        for ch in chunks:
            web = getattr(ch, "web", None)
            uri = getattr(web, "uri", None)
            if uri:
                urls.append(uri)
    return list(dict.fromkeys(urls))


def _trace_loop(root: Any, name: str, rounds: Optional[list[dict[str, Any]]]) -> None:
    """差し戻しループを親スパン＋各ラウンドの子スパンで可視化する（空なら何もしない）。"""
    items = list(rounds or [])
    if not items:
        return
    span = root.start_span(name=name, metadata={"rounds": len(items)})
    for v in items:
        child = span.start_span(name=f"{name}_r{v.get('round')}", metadata=v)
        child.end()
    span.end()


def trace_pipeline(payload: dict[str, Any], *, client: Any = None) -> str:
    """2つの差し戻しループ＋grounding URL を1トレースで送る（C5.6）。

    payload（すべて任意）:
      - theme: str
      - approved: bool
      - planning_rounds: [{round, score, decision}]   … 対立①（企画リーダー差し戻し）
      - editing_rounds:  [{round, ...}]                … 対立②（編集長の本文差し戻し）
      - grounding_urls:  [str]                         … 調査の grounding 取得URL

    キー未設定/langfuse未導入なら no-op。戻り値は "sent"/"skipped..."/"error..."。
    `client` を渡すとそれを使う（テスト用シーム）。
    """
    lf = client if client is not None else _client()
    if lf is None:
        return "skipped (langfuse未導入 or LANGFUSE_*キー未設定)"
    try:
        grounding = list(payload.get("grounding_urls") or [])
        root = lf.start_span(
            name="publishr-pipeline",
            input={"theme": payload.get("theme")},
            metadata={
                "approved": bool(payload.get("approved")),
                "groundingCount": len(grounding),
            },
        )
        _trace_loop(root, "planning_loop", payload.get("planning_rounds"))
        _trace_loop(root, "editing_loop", payload.get("editing_rounds"))
        if grounding:
            g = root.start_span(name="grounding", metadata={"urls": grounding})
            g.end()
        root.update(output={"approved": bool(payload.get("approved"))})
        root.end()
        lf.flush()
        return "sent"
    except Exception as e:  # 計装失敗は致命ではない
        return f"error: {type(e).__name__}: {e}"


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
