"""観測ソースの抽象と dispatcher。

`PUBLISHR_OBSERVE` で差し替える（既定 fixture＝オフライン決定的／google＝実API・隔離）。
`PUBLISHR_LLM`・`DATA_SOURCE` と同じシーム方針。
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Protocol

from publishr_schema import ObservationBundle, User


class ObservationSource(Protocol):
    """3ソースを束ねて ObservationBundle を返す。実装は決定的後処理を transform に委ねる。"""

    def collect(self, user: User, *, now: datetime) -> ObservationBundle: ...


def _default_source() -> ObservationSource:
    mode = os.environ.get("PUBLISHR_OBSERVE", "fixture").lower()
    if mode == "fixture":
        from .fixture_source import FixtureObservationSource

        return FixtureObservationSource()
    if mode == "google":
        # 実Google API。google-api-python-client 等を遅延 import（オフライン既定を汚さない）。
        from .google_source import GoogleObservationSource

        return GoogleObservationSource()
    raise ValueError(f"unknown PUBLISHR_OBSERVE={mode!r}")


def collect_observation(
    user: User,
    *,
    now: datetime,
    source: Optional[ObservationSource] = None,
) -> ObservationBundle:
    """STEP0 観測ツールの入口。source 未指定なら PUBLISHR_OBSERVE で解決する。

    now は呼び出し側が渡す（ライブラリ内に隠れ時計を持たない＝決定的）。
    """
    src = source or _default_source()
    return src.collect(user, now=now)
