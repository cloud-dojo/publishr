"""エラー/リトライ/冪等/タイムアウトの最小方針（C5.9・I-20）。

## 方針（最小ルール）

- **timeout**: 実LLM呼び出し（Vertex/ADK runner）は1試行ごとに `timeout_seconds` で打ち切る。
  超過は `TimeoutError` → transient 扱い（リトライ対象）。既定タイムアウトは
  `RuntimeProfile.timeout_seconds`（dev=45s / prod=300s）に合わせる。
- **retry**: transient なエラー（タイムアウト・503/UNAVAILABLE・429/RESOURCE_EXHAUSTED・
  一時的な接続断）**のみ**、指数バックオフで最大 `PUBLISHR_RETRY_MAX` 回（既定2回＝計3試行）
  リトライする。非 transient（スキーマ違反・不正リクエスト・`CostGuardError` 等）は即時送出し、
  無駄な再試行と課金を避ける。
- **冪等性 (I-20)**: 状態遷移は「writeable 状態でなければ skip」で二重実行を防ぐ
  （`apps/api/publishr_api/services/reservation_service.process_write_job`）。Pub/Sub の再配信や
  本リトライによる重複に耐える。
- **コスト規律**: retry はコストを増やすため上限必須。**mock 経路はこのモジュールを通らない**
  （決定的・課金ゼロ）。実LLM経路（`PUBLISHR_LLM=vertex`）のみで使う。

バックオフは jitter なし＝決定的にしてテスト容易性を優先する（単一呼び出しの最小方針）。
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping, Optional, TypeVar

T = TypeVar("T")

# transient と判定するエラー型名（google-api / ADK 由来を SDK 非依存で名前で拾う）
_TRANSIENT_TYPE_NAMES = frozenset(
    {
        "TimeoutError",
        "ServiceUnavailable",
        "ResourceExhausted",
        "InternalServerError",
        "DeadlineExceeded",
        "Aborted",
        "ConnectionError",
        "TooManyRequests",
    }
)

# transient と判定するメッセージ断片（HTTP/gRPC コードや一時障害の語）
_TRANSIENT_MSG_HINTS = (
    "503",
    "429",
    "unavailable",
    "deadline",
    "timeout",
    "timed out",
    "rate limit",
    "resource exhausted",
    "temporarily",
)


def is_transient(err: BaseException) -> bool:
    """一時的（リトライで回復しうる）エラーかを型名とメッセージから判定する。"""
    if type(err).__name__ in _TRANSIENT_TYPE_NAMES:
        return True
    msg = str(err).lower()
    return any(hint in msg for hint in _TRANSIENT_MSG_HINTS)


@dataclass(frozen=True)
class RetryPolicy:
    """リトライ方針。`max_retries` は追加試行回数（計 max_retries+1 試行）。"""

    max_retries: int = 2
    base_delay: float = 0.5
    max_delay: float = 8.0
    timeout_seconds: Optional[float] = None  # 1試行のタイムアウト（None=無効）

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "RetryPolicy":
        values = os.environ if env is None else env

        def _int(name: str, default: int) -> int:
            raw = values.get(name)
            return int(raw) if raw not in (None, "") else default

        def _float(name: str, default: float) -> float:
            raw = values.get(name)
            return float(raw) if raw not in (None, "") else default

        timeout = _float("PUBLISHR_TIMEOUT_SECONDS", 0.0)
        return cls(
            max_retries=_int("PUBLISHR_RETRY_MAX", 2),
            base_delay=_float("PUBLISHR_RETRY_BASE_DELAY", 0.5),
            max_delay=_float("PUBLISHR_RETRY_MAX_DELAY", 8.0),
            timeout_seconds=(timeout or None),
        )


def backoff_delay(attempt: int, policy: RetryPolicy) -> float:
    """attempt（0始まり）に対する待機秒。指数バックオフを max_delay で上限留め。"""
    return min(policy.max_delay, policy.base_delay * (2**attempt))


OnRetry = Callable[[int, BaseException, float], None]


def run_with_retry(
    fn: Callable[[], T],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: Optional[OnRetry] = None,
) -> T:
    """同期版。transient のみ指数バックオフでリトライ。`sleep` 注入でテスト容易。"""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as err:  # CancelledError(BaseException) は捕まえない
            if attempt >= policy.max_retries or not is_transient(err):
                raise
            delay = backoff_delay(attempt, policy)
            if on_retry is not None:
                on_retry(attempt + 1, err, delay)
            sleep(delay)
            attempt += 1


async def run_with_retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    on_retry: Optional[OnRetry] = None,
) -> T:
    """非同期版。`timeout_seconds` 指定時は1試行を `asyncio.wait_for` で打ち切る。"""
    attempt = 0
    while True:
        try:
            if policy.timeout_seconds:
                return await asyncio.wait_for(fn(), timeout=policy.timeout_seconds)
            return await fn()
        except Exception as err:  # CancelledError(BaseException) は捕まえない
            if attempt >= policy.max_retries or not is_transient(err):
                raise
            delay = backoff_delay(attempt, policy)
            if on_retry is not None:
                on_retry(attempt + 1, err, delay)
            await sleep(delay)
            attempt += 1
