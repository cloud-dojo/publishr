"""STEP0 観測ツール（非エージェント・決定的）。

Drive/Calendar/Tasks（±14日・Drive は Picker 選択 folderIds 配下のみ）を束ねて
ObservationBundle(§2) を生成する。既定はオフライン fixture、実APIは PUBLISHR_OBSERVE=google。
"""

from __future__ import annotations

from .fixture_source import FixtureObservationSource
from .source import ObservationSource, collect_observation

__all__ = [
    "ObservationSource",
    "collect_observation",
    "FixtureObservationSource",
]
