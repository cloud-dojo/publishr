"""モードA: 企画会議パイプラインを起動し、結果をリポジトリへ反映する。"""

from __future__ import annotations

from publishr_agents import PipelineResult, run_pipeline

from ..repositories.protocol import RepositoryProtocol


def run(repo: RepositoryProtocol, user_id: str) -> PipelineResult:
    result = run_pipeline(user_id)
    for book in result.books:
        repo.upsert_book(book)
    return result
