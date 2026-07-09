"""実LLM実行プロファイルと呼び出し前コストガード（P0b）。

P2 以降の Vertex 呼び出しは、このモジュールで上限確認とログ整形を行ってから実行する。
mock 経路では未使用。
"""

from __future__ import annotations

import builtins
import os
import uuid
from dataclasses import dataclass
from typing import Mapping


class CostGuardError(RuntimeError):
    """実LLM呼び出し前に実行上限を超えたときの停止理由。"""


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    run_id: str
    max_iterations: int
    max_books_per_run: int
    body_pages_min: int
    body_pages_max: int
    # モードB本文の「本全体」目標文字数（I-35・章立てに応じて著者へ注入＝{{body_volume}}）。
    # dev は安く短く、prod は 1万〜2万字帯。章単位の目安は body_char_target ÷ 採用章数で導出する。
    body_char_target: int
    enable_imagen: bool
    editor_rounds: int
    timeout_seconds: int
    max_estimated_cost_jpy: float


@dataclass(frozen=True)
class EstimatedUsage:
    run_id: str
    model: str
    round: int
    input_tokens: int
    output_tokens: int
    estimated_cost_jpy: float


_DEV_DEFAULTS = {
    "max_iterations": 3,
    "max_books_per_run": 2,
    "body_pages_min": 3,
    "body_pages_max": 5,
    "body_char_target": 1_500,
    "enable_imagen": False,
    "editor_rounds": 1,
    "timeout_seconds": 45,
    "max_estimated_cost_jpy": 100.0,
}

_PROD_DEFAULTS = {
    "max_iterations": 3,
    "max_books_per_run": 4,
    "body_pages_min": 3,
    "body_pages_max": 100,
    "body_char_target": 12_000,
    "enable_imagen": True,
    "editor_rounds": 3,
    "timeout_seconds": 300,
    "max_estimated_cost_jpy": 2_000.0,
}

_MODEL_COST_JPY_PER_MTOKEN = {
    "pro": (350.0, 1_050.0),
    "flash": (50.0, 200.0),
}


def _env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def _run_id(values: Mapping[str, str]) -> str:
    return values.get("PUBLISHR_RUN_ID") or f"run_{uuid.uuid4().hex[:12]}"


def _int(values: Mapping[str, str], name: str, default: int) -> int:
    raw = values.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _float(values: Mapping[str, str], name: str, default: float) -> float:
    raw = values.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _bool(values: Mapping[str, str], name: str, default: bool) -> bool:
    raw = values.get(name)
    if raw is None or raw == "":
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def profile_from_env(env: Mapping[str, str] | None = None) -> RuntimeProfile:
    """環境変数から実LLM実行プロファイルを作る。未指定は安全側の dev。"""

    values = _env(env)
    name = values.get("PUBLISHR_RUN_PROFILE", "dev").lower()
    if name == "dev":
        defaults = _DEV_DEFAULTS
    elif name == "prod":
        defaults = _PROD_DEFAULTS
    else:
        raise ValueError(f"unknown PUBLISHR_RUN_PROFILE={name!r}")

    return RuntimeProfile(
        name=name,
        run_id=_run_id(values),
        max_iterations=_int(values, "PUBLISHR_MAX_ITERATIONS", defaults["max_iterations"]),
        max_books_per_run=_int(
            values, "PUBLISHR_MAX_BOOKS_PER_RUN", defaults["max_books_per_run"]
        ),
        body_pages_min=_int(values, "PUBLISHR_BODY_PAGES_MIN", defaults["body_pages_min"]),
        body_pages_max=_int(values, "PUBLISHR_MAX_BODY_PAGES", defaults["body_pages_max"]),
        body_char_target=_int(values, "PUBLISHR_BODY_CHAR_TARGET", defaults["body_char_target"]),
        enable_imagen=_bool(values, "ENABLE_IMAGEN", defaults["enable_imagen"]),
        editor_rounds=_int(values, "PUBLISHR_EDITOR_ROUNDS", defaults["editor_rounds"]),
        timeout_seconds=_int(values, "PUBLISHR_TIMEOUT_SECONDS", defaults["timeout_seconds"]),
        max_estimated_cost_jpy=_float(
            values,
            "PUBLISHR_MAX_ESTIMATED_COST_JPY",
            defaults["max_estimated_cost_jpy"],
        ),
    )


def guard_vertex_call(
    *,
    usage: EstimatedUsage,
    profile: RuntimeProfile,
    iterations: int,
    books: int,
    body_pages: int,
    imagen_requested: bool,
) -> dict[str, object]:
    """Vertex 呼び出し前に実行上限を確認し、通過時はログ用dictを返す。"""

    abort_reason = _abort_reason(
        usage=usage,
        profile=profile,
        iterations=iterations,
        books=books,
        body_pages=body_pages,
        imagen_requested=imagen_requested,
    )
    if abort_reason:
        raise CostGuardError(abort_reason)
    return usage_log(usage, profile, abort_reason=None)


def estimate_usage(
    *,
    run_id: str,
    model: str,
    round: int,
    input_text: str,
    expected_output_tokens: int,
) -> EstimatedUsage:
    """Vertex 呼び出し前の概算 usage を作る。

    token 数は安全側の簡易見積もり（日本語/英語混在を4文字=1token相当）で、P2 の
    実ランタイムでは実測 usage と合わせてログに残す。
    """

    input_tokens = max(1, len(input_text) // 4)
    input_rate, output_rate = _rates_for_model(model)
    estimated_cost_jpy = builtins.round(
        (input_tokens * input_rate + expected_output_tokens * output_rate) / 1_000_000,
        4,
    )
    return EstimatedUsage(
        run_id=run_id,
        model=model,
        round=round,
        input_tokens=input_tokens,
        output_tokens=expected_output_tokens,
        estimated_cost_jpy=estimated_cost_jpy,
    )


def usage_log(
    usage: EstimatedUsage,
    profile: RuntimeProfile,
    *,
    abort_reason: str | None,
) -> dict[str, object]:
    return {
        "run_id": usage.run_id,
        "profile": profile.name,
        "model": usage.model,
        "round": usage.round,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_jpy": usage.estimated_cost_jpy,
        "abort_reason": abort_reason,
    }


def _abort_reason(
    *,
    usage: EstimatedUsage,
    profile: RuntimeProfile,
    iterations: int,
    books: int,
    body_pages: int,
    imagen_requested: bool,
) -> str | None:
    if iterations > profile.max_iterations:
        return f"max_iterations exceeded: {iterations}>{profile.max_iterations}"
    if books > profile.max_books_per_run:
        return f"max_books_per_run exceeded: {books}>{profile.max_books_per_run}"
    if body_pages > profile.body_pages_max:
        return f"max_body_pages exceeded: {body_pages}>{profile.body_pages_max}"
    if imagen_requested and not profile.enable_imagen:
        return "ENABLE_IMAGEN is false"
    if usage.estimated_cost_jpy > profile.max_estimated_cost_jpy:
        return (
            "estimated_cost_jpy exceeded: "
            f"{usage.estimated_cost_jpy}>{profile.max_estimated_cost_jpy}"
        )
    return None


def _rates_for_model(model: str) -> tuple[float, float]:
    model_lower = model.lower()
    if "flash" in model_lower:
        return _MODEL_COST_JPY_PER_MTOKEN["flash"]
    return _MODEL_COST_JPY_PER_MTOKEN["pro"]
