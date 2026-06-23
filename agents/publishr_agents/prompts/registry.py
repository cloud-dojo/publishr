"""STEP/role → プロンプトファイル・モデル・出力スキーマ・state key のレジストリ（P0bシーム）。

few-shot 注入規律（packages/prompts/README §4）の単一情報源：
採点系（leader / editor×2 / judge）は few-shot 常時ON、生成系は PROMPT_FEWSHOT 依存。
**mock経路では未使用**。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Type

from publishr_schema import (
    BodyVerdict,
    BookDraft,
    EditorialIntent,
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
    # v3（4テーマ1-1-1-1）：editorial_intent → 調査3サブ → plan_owner(PlanProposal×4) → plan_leader(LeaderVerdict)
    # PlanSet/PlanSetVerdict は v3移行完了後に使用予定（プロンプト・テスト整備後）
    "editorial_intent": StepSpec(
        "editorial_intent", "step2_editorial_intent", "editorial_intent",
        False, False, EditorialIntent, K.EDITORIAL_INTENT,
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
