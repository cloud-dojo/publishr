"""C5.6 Langfuse計装（2ループ＋grounding URL）の決定的テスト。

Langfuse 実SDK/キーに依存せず、record する fake client を注入して、
①企画リーダー差し戻しループ ②編集長の本文ループ ③grounding URL が
1トレースのスパン構造として送られることを検証する。キー未設定なら no-op。
正本: docs/planning/wbs.md C5.6。
"""

from __future__ import annotations

from types import SimpleNamespace

from publishr_agents.observability import grounding_urls_from_events, trace_pipeline


class _FakeSpan:
    def __init__(self, log: list, name: str):
        self.log = log
        self.name = name

    def start_span(self, name: str, **kw):
        self.log.append(("span", name))
        return _FakeSpan(self.log, name)

    def update(self, **kw):
        self.log.append(("update", self.name))

    def end(self):
        self.log.append(("end", self.name))


class _FakeClient:
    def __init__(self):
        self.log: list = []
        self.flushed = False

    def start_span(self, name: str, **kw):
        self.log.append(("span", name))
        return _FakeSpan(self.log, name)

    def flush(self):
        self.flushed = True


_PAYLOAD = {
    "theme": "新任マネージャーの任せ方",
    "approved": True,
    "planning_rounds": [
        {"round": 1, "score": 62, "decision": "却下"},
        {"round": 2, "score": 81, "decision": "採用"},
    ],
    "editing_rounds": [
        {"round": 1, "score": 64, "decision": "revise"},
        {"round": 2, "score": 80, "decision": "approve"},
    ],
    "grounding_urls": ["https://example.com/a", "https://example.com/b"],
}


def test_trace_pipeline_noop_without_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    status = trace_pipeline(_PAYLOAD)  # client未指定→_client()→キー無→None
    assert status.startswith("skipped")


def test_trace_pipeline_records_both_loops_and_grounding():
    client = _FakeClient()
    status = trace_pipeline(_PAYLOAD, client=client)
    assert status == "sent"
    assert client.flushed is True

    spans = [name for kind, name in client.log if kind == "span"]
    # ルート＋2ループ＋各ループ2ラウンド＋grounding
    assert "publishr-pipeline" in spans
    assert "planning_loop" in spans
    assert "editing_loop" in spans
    assert "planning_loop_r1" in spans and "planning_loop_r2" in spans
    assert "editing_loop_r1" in spans and "editing_loop_r2" in spans
    assert "grounding" in spans
    # ルートは update（output）と end を経ている
    assert ("update", "publishr-pipeline") in client.log
    assert ("end", "publishr-pipeline") in client.log


def test_trace_pipeline_partial_payload_only_one_loop():
    """編集ループだけ（mode_b単体）でも壊れず、planning スパンは作らない。"""
    client = _FakeClient()
    status = trace_pipeline(
        {"editing_rounds": [{"round": 1, "score": 80, "decision": "approve"}]},
        client=client,
    )
    assert status == "sent"
    spans = [name for kind, name in client.log if kind == "span"]
    assert "editing_loop" in spans
    assert "planning_loop" not in spans
    assert "grounding" not in spans


def _web(uri: str):
    return SimpleNamespace(web=SimpleNamespace(uri=uri))


def test_grounding_urls_extracted_deduped_ordered():
    ev1 = SimpleNamespace(
        grounding_metadata=SimpleNamespace(grounding_chunks=[_web("https://a"), _web("https://b")])
    )
    ev2 = SimpleNamespace(
        grounding_metadata=SimpleNamespace(grounding_chunks=[_web("https://b"), _web("https://c")])
    )
    ev3 = SimpleNamespace(grounding_metadata=None)  # 未grounding
    urls = grounding_urls_from_events([ev1, ev2, ev3])
    assert urls == ["https://a", "https://b", "https://c"]  # 重複除去・順序保持


def test_grounding_urls_empty_on_no_events():
    assert grounding_urls_from_events(None) == []
    assert grounding_urls_from_events([SimpleNamespace()]) == []
