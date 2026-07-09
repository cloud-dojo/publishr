"""C5.9 エラー/リトライ/冪等/タイムアウト方針の決定的テスト。

実LLM経路のレジリエンス（transient分類・指数バックオフ・最大試行・タイムアウト）を、
実際の sleep / LLM を呼ばず（sleep を注入）に決定的に検証する。正本: docs/planning/wbs.md C5.9。
"""

from __future__ import annotations

import asyncio

import pytest

from publishr_agents.llm.resilience import (
    RetryPolicy,
    backoff_delay,
    is_transient,
    run_with_retry,
    run_with_retry_async,
)


class _Boom(Exception):
    """テスト用の汎用（非transient）例外。"""


# --- is_transient ---------------------------------------------------------
def test_is_transient_by_type_name():
    assert is_transient(TimeoutError("deadline"))
    assert is_transient(type("ServiceUnavailable", (Exception,), {})("x"))
    assert is_transient(type("ResourceExhausted", (Exception,), {})("x"))


def test_is_transient_by_message_hint():
    assert is_transient(Exception("HTTP 503 Service Unavailable"))
    assert is_transient(Exception("429 rate limit exceeded"))
    assert is_transient(Exception("temporarily unavailable"))


def test_non_transient_errors_not_retried_class():
    assert not is_transient(ValueError("invalid schema field"))
    assert not is_transient(_Boom("logic error"))


# --- backoff --------------------------------------------------------------
def test_backoff_is_exponential_and_capped():
    p = RetryPolicy(base_delay=0.5, max_delay=4.0)
    assert backoff_delay(0, p) == 0.5
    assert backoff_delay(1, p) == 1.0
    assert backoff_delay(2, p) == 2.0
    assert backoff_delay(3, p) == 4.0
    assert backoff_delay(10, p) == 4.0  # capped


def test_policy_from_env_reads_overrides():
    p = RetryPolicy.from_env({"PUBLISHR_RETRY_MAX": "5", "PUBLISHR_RETRY_BASE_DELAY": "0.1"})
    assert p.max_retries == 5
    assert p.base_delay == 0.1
    # 既定（未指定）
    d = RetryPolicy.from_env({})
    assert d.max_retries == 2


# --- run_with_retry (sync) ------------------------------------------------
def test_succeeds_first_try_no_retry():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "ok"

    assert run_with_retry(fn, policy=RetryPolicy(), sleep=lambda _: None) == "ok"
    assert calls["n"] == 1


def test_retries_transient_then_succeeds():
    calls = {"n": 0}
    slept: list[float] = []

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("deadline exceeded")
        return "ok"

    out = run_with_retry(
        fn, policy=RetryPolicy(max_retries=3, base_delay=0.5), sleep=slept.append
    )
    assert out == "ok"
    assert calls["n"] == 3
    assert slept == [0.5, 1.0]  # 2回の待機（指数）


def test_gives_up_after_max_retries():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise TimeoutError("still down")

    with pytest.raises(TimeoutError):
        run_with_retry(fn, policy=RetryPolicy(max_retries=2), sleep=lambda _: None)
    assert calls["n"] == 3  # 1 + max_retries


def test_non_transient_raises_immediately():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise _Boom("bad request")

    with pytest.raises(_Boom):
        run_with_retry(fn, policy=RetryPolicy(max_retries=5), sleep=lambda _: None)
    assert calls["n"] == 1  # リトライしない


def test_on_retry_callback_invoked():
    seen: list[int] = []

    def fn():
        if len(seen) < 1:
            raise TimeoutError("x")
        return 1

    run_with_retry(
        fn,
        policy=RetryPolicy(max_retries=2),
        sleep=lambda _: None,
        on_retry=lambda attempt, err, delay: seen.append(attempt),
    )
    assert seen == [1]


# --- run_with_retry_async + timeout ---------------------------------------
def test_async_retries_then_succeeds():
    calls = {"n": 0}
    slept: list[float] = []

    async def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutError("deadline")
        return "ok"

    async def fake_sleep(d):
        slept.append(d)

    out = asyncio.run(
        run_with_retry_async(fn, policy=RetryPolicy(max_retries=2), sleep=fake_sleep)
    )
    assert out == "ok"
    assert calls["n"] == 2
    assert slept == [0.5]


def test_async_timeout_is_transient_and_retried():
    calls = {"n": 0}
    slept: list[float] = []

    async def slow():
        calls["n"] += 1
        await asyncio.sleep(10)  # タイムアウトに必ずかかる

    async def fake_sleep(d):
        slept.append(d)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(
            run_with_retry_async(
                slow,
                policy=RetryPolicy(max_retries=1, timeout_seconds=0.01),
                sleep=fake_sleep,
            )
        )
    assert calls["n"] == 2  # タイムアウト→transient→1回リトライ→計2試行
