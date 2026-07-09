"""モードA: 企画会議パイプラインを起動し、結果をリポジトリへ反映する。

実体は `mode_a_service`（観測→読者→企画→キャスティング→プレビュー→装丁→arrivals永続）。
旧 canned v1（`run_pipeline`）からの差替後も `/pipeline/run` の入口を保つための薄い委譲。
"""

from __future__ import annotations

from publishr_agents import PipelineResult

from ..repositories.protocol import RepositoryProtocol
from . import mode_a_service


def run(repo: RepositoryProtocol, user_id: str) -> PipelineResult:
    return mode_a_service.run(repo, user_id)
