from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from publishr_agents import PipelineResult

from ..config import settings
from ..deps import get_repository
from ..repositories.protocol import RepositoryProtocol
from ..schemas import PipelineRunInput
from ..services import pipeline_service

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _require_exposed() -> None:
    # 本番（PUBLISHR_ALLOW_PIPELINE_RUN=0）ではこの素ルートを閉じる（実Vertex課金の無ガード入口封じ）。
    if not settings.allow_pipeline_run:
        raise HTTPException(status_code=403, detail="このエンドポイントは公開されていません")


@router.post("/run", response_model=PipelineResult, dependencies=[Depends(_require_exposed)])
def run_pipeline(
    payload: PipelineRunInput,
    repo: RepositoryProtocol = Depends(get_repository),
) -> PipelineResult:
    """企画会議（モードA）を起動し、入荷書籍を生成。reject_log（却下→再提出）を返す。

    dev/テスト用の素の入口（ガード無し）。許可uid・レート制限・実行中ロックが要る公開導線は
    `POST /api/trigger/planning`（routers/api.py）を使う。本番では PUBLISHR_ALLOW_PIPELINE_RUN=0
    で 403 に閉じる。
    """
    return pipeline_service.run(repo, payload.user_id)
