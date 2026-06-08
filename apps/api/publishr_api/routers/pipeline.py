from __future__ import annotations

from fastapi import APIRouter, Depends
from publishr_agents import PipelineResult

from ..deps import get_repository
from ..repositories.protocol import RepositoryProtocol
from ..schemas import PipelineRunInput
from ..services import pipeline_service

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineResult)
def run_pipeline(
    payload: PipelineRunInput,
    repo: RepositoryProtocol = Depends(get_repository),
) -> PipelineResult:
    """企画会議（モードA）を起動し、入荷書籍を生成。reject_log（却下→再提出）を返す。

    dev/テスト用の素の入口（ガード無し）。許可uid・レート制限・実行中ロックが要る公開導線は
    `POST /api/trigger/planning`（routers/api.py）を使う。本番ではこの素ルートは公開しない。
    """
    return pipeline_service.run(repo, payload.user_id)
