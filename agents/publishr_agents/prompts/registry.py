"""STEP/role → プロンプトファイル・モデル・出力スキーマ・state key のレジストリ（P0bシーム）。

few-shot 注入規律（packages/prompts/README §4）の単一情報源：
採点系（leader / editor×2 / judge）は few-shot 常時ON、生成系は PROMPT_FEWSHOT 依存。
**mock経路では未使用**。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Type

from publishr_schema import (
    AuthorCasting,
    BodyVerdict,
    BookDraft,
    EditorVerdict,
    GeneratedPersonaSet,
    LeaderVerdict,
    PlanProposal,
    PlanSet,
    PlanSetVerdict,
    ReaderProfile3Layer,
    SerendipitySet,
    SubMarket,
    SubReaderContext,
    SubThemeInsight,
    SubTrendInsight,
    ThemeAssignmentSet,
)
from pydantic import BaseModel

from .. import state_keys as K


@dataclass(frozen=True)
class StepSpec:
    role: str
    prompt_file: str
    model_role: str  # llm.provider._ROLE_TIER のキーと一致
    is_scoring: bool
    fewshot_always_on: bool
    output_schema: Optional[Type[BaseModel]]
    output_key: Optional[str]


REGISTRY: dict[str, StepSpec] = {
    "reader_analyst": StepSpec(
        "reader_analyst", "step1_reader_analyst", "reader_analyst",
        False, False, ReaderProfile3Layer, K.READER_PROFILE,
    ),
    "sub_reader_context": StepSpec(
        "sub_reader_context", "step2_research_subs", "sub_reader_context",
        False, False, SubReaderContext, K.SUB_READER_CONTEXT,
    ),
    "sub_market": StepSpec(
        "sub_market", "step2_research_subs", "sub_market",
        False, False, SubMarket, K.SUB_MARKET,
    ),
    "sub_theme_insight": StepSpec(
        "sub_theme_insight", "step2_research_subs", "sub_theme_insight",
        False, False, SubThemeInsight, K.SUB_THEME_INSIGHT,
    ),
    "plan_owner": StepSpec(
        "plan_owner", "step2_plan_owner", "plan_owner",
        False, False, PlanProposal, K.PLAN_DRAFT,
    ),
    "plan_leader": StepSpec(
        "plan_leader", "step2_plan_leader", "plan_leader",
        True, True, LeaderVerdict, K.LEADER_VERDICT,
    ),
    "serendipity_themes": StepSpec(
        "serendipity_themes", "step2_serendipity_themes", "serendipity_themes",
        False, False, SerendipitySet, K.SERENDIPITY_SET,
    ),
    # ── v3 4テーマ1-1-1-1（予約制廃止改定 2026-06-23）。新プロンプト群へ配線。旧roleは実パイプライン移行まで併存 ──
    # 編集長テーマ設定 → 各チーム[調査3(今/市場/普遍)→plan_owner→plan_leader] → 編集長セットゲート → author_casting
    "editor_chief_themes": StepSpec(
        "editor_chief_themes", "step2_editor_chief_themes", "editor_chief_themes",
        False, False, ThemeAssignmentSet, K.THEME_ASSIGNMENT_SET,
    ),
    "sub_trend": StepSpec(
        "sub_trend", "step2_research_trend", "sub_trend",
        False, False, SubTrendInsight, K.SUB_TREND,
    ),
    "sub_competitors": StepSpec(
        "sub_competitors", "step2_research_competitors", "sub_competitors",
        False, False, SubMarket, K.SUB_MARKET,
    ),
    "sub_classics": StepSpec(
        "sub_classics", "step2_research_classics", "sub_classics",
        False, False, SubThemeInsight, K.SUB_THEME_INSIGHT,
    ),
    "editor_chief_gate": StepSpec(
        "editor_chief_gate", "step2_editor_chief_gate", "editor_chief_gate",
        True, True, PlanSetVerdict, K.PLAN_SET_VERDICT,
    ),
    "author_casting": StepSpec(
        "author_casting", "step3_author_casting", "author_casting",
        False, False, AuthorCasting, K.AUTHOR_CASTING,
    ),
    "persona_generator": StepSpec(
        "persona_generator", "step3_casting_editor", "persona_generator",
        False, False, GeneratedPersonaSet, K.GENERATED_PERSONA_SET,
    ),
    "author_preview": StepSpec(
        "author_preview", "step4_author_preview", "author_preview",
        False, False, BookDraft, None,
    ),
    "editor_preview": StepSpec(
        "editor_preview", "step4_editor_preview", "editor_preview",
        True, True, EditorVerdict, K.EDITOR_VERDICT,
    ),
    "cover": StepSpec(
        "cover", "step5_cover", "cover",
        False, False, None, None,
    ),
    "modeb_author": StepSpec(
        "modeb_author", "modeB_author_body", "modeb_author",
        False, False, None, None,
    ),
    "modeb_editor": StepSpec(
        "modeb_editor", "modeB_editor_body", "modeb_editor",
        True, True, BodyVerdict, K.EDITOR_VERDICT,
    ),
    "eval_judge": StepSpec(
        "eval_judge", "eval_judge", "eval_judge",
        True, True, LeaderVerdict, None,
    ),
}


def spec_for(role: str) -> StepSpec:
    try:
        return REGISTRY[role]
    except KeyError as exc:
        raise KeyError(f"unknown step role: {role!r}") from exc
