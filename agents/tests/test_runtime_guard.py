"""実LLM実行プロファイルとコストガードのテスト（H0b）。"""

from __future__ import annotations

import pytest

from publishr_agents.llm.runtime import (
    CostGuardError,
    EstimatedUsage,
    estimate_usage,
    guard_vertex_call,
    profile_from_env,
)


def test_dev_profile_is_default_and_keeps_vertex_small():
    profile = profile_from_env({})

    assert profile.name == "dev"
    assert profile.max_books_per_run == 2
    assert profile.body_pages_max == 5
    assert profile.body_char_target == 1_500
    assert profile.editor_rounds == 1
    assert profile.enable_imagen is False
    assert profile.timeout_seconds <= 60


def test_prod_profile_requires_explicit_env():
    profile = profile_from_env({"PUBLISHR_RUN_PROFILE": "prod"})

    assert profile.name == "prod"
    assert profile.max_books_per_run == 4
    assert profile.body_pages_max >= 100
    assert profile.body_char_target == 12_000
    assert profile.editor_rounds == 3
    assert profile.enable_imagen is True


def test_body_char_target_env_override():
    """本全体目標文字数は PUBLISHR_BODY_CHAR_TARGET で上書きできる（I-35・パラメータ化）。"""
    profile = profile_from_env({"PUBLISHR_BODY_CHAR_TARGET": "8000"})
    assert profile.body_char_target == 8_000


def test_guard_blocks_before_vertex_when_dev_limits_are_exceeded():
    profile = profile_from_env({})
    usage = EstimatedUsage(
        run_id="run_test",
        model="gemini-2.5-pro",
        round=1,
        input_tokens=100,
        output_tokens=100,
        estimated_cost_jpy=1.0,
    )

    with pytest.raises(CostGuardError, match="max_books_per_run"):
        guard_vertex_call(
            usage=usage,
            profile=profile,
            iterations=1,
            books=3,
            body_pages=3,
            imagen_requested=False,
        )


def test_guard_blocks_imagen_and_estimated_cost_in_dev():
    profile = profile_from_env({"PUBLISHR_MAX_ESTIMATED_COST_JPY": "10"})
    usage = EstimatedUsage(
        run_id="run_test",
        model="gemini-2.5-pro",
        round=1,
        input_tokens=10_000,
        output_tokens=10_000,
        estimated_cost_jpy=11.0,
    )

    with pytest.raises(CostGuardError, match="ENABLE_IMAGEN"):
        guard_vertex_call(
            usage=usage,
            profile=profile,
            iterations=1,
            books=1,
            body_pages=3,
            imagen_requested=True,
        )

    with pytest.raises(CostGuardError, match="estimated_cost_jpy"):
        guard_vertex_call(
            usage=usage,
            profile=profile,
            iterations=1,
            books=1,
            body_pages=3,
            imagen_requested=False,
        )


def test_guard_returns_cost_log_when_within_limits():
    profile = profile_from_env({"PUBLISHR_RUN_ID": "run_fixed"})
    usage = EstimatedUsage(
        run_id=profile.run_id,
        model="gemini-2.5-flash",
        round=2,
        input_tokens=120,
        output_tokens=80,
        estimated_cost_jpy=0.5,
    )

    log = guard_vertex_call(
        usage=usage,
        profile=profile,
        iterations=2,
        books=2,
        body_pages=5,
        imagen_requested=False,
    )

    assert log == {
        "run_id": "run_fixed",
        "profile": "dev",
        "model": "gemini-2.5-flash",
        "round": 2,
        "input_tokens": 120,
        "output_tokens": 80,
        "estimated_cost_jpy": 0.5,
        "abort_reason": None,
    }


def test_estimate_usage_builds_pre_call_token_and_cost_record():
    usage = estimate_usage(
        run_id="run_est",
        model="gemini-2.5-pro",
        round=1,
        input_text="abcd" * 100,
        expected_output_tokens=200,
    )

    assert usage.run_id == "run_est"
    assert usage.input_tokens == 100
    assert usage.output_tokens == 200
    assert usage.estimated_cost_jpy > 0
