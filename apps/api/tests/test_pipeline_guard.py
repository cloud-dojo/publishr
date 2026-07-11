"""/pipeline/run の露出ガード（P0 ハードニング）。

素ルート `/pipeline/run` はレート制限も所有者検証も無い dev/テスト用の入口。
- 本番既定（PUBLISHR_ALLOW_PIPELINE_RUN=0）では 403 に閉じる。
- さらに実LLM(vertex)構成では allow_pipeline_run に関わらず常に閉じる＝env ドリフトで
  フラグが True に戻っても、無制限に実Vertex課金される入口にならないための code 側 backstop。
  課金は必ずレートcap付きの /api/trigger/planning を通す。
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from publishr_api.config import settings
from publishr_api.routers.pipeline import _require_exposed


def test_closed_when_not_allowed(monkeypatch):
    monkeypatch.setattr(settings, "allow_pipeline_run", False)
    monkeypatch.setattr(settings, "publishr_llm", "mock")
    with pytest.raises(HTTPException) as ei:
        _require_exposed()
    assert ei.value.status_code == 403


def test_open_for_mock_when_allowed(monkeypatch):
    # dev/mock で明示許可された素ルートは通す（例外が出なければ OK）。
    monkeypatch.setattr(settings, "allow_pipeline_run", True)
    monkeypatch.setattr(settings, "publishr_llm", "mock")
    _require_exposed()


def test_forced_closed_under_vertex_even_if_allowed(monkeypatch):
    # env ドリフトで allow_pipeline_run=1 のまま vertex になっても素ルートは必ず閉じる。
    monkeypatch.setattr(settings, "allow_pipeline_run", True)
    monkeypatch.setattr(settings, "publishr_llm", "vertex")
    with pytest.raises(HTTPException) as ei:
        _require_exposed()
    assert ei.value.status_code == 403
