"""Publishr v2 エージェントI/Oモデル（ADK output_schema 用・pydantic v2）。

モードA/Bの各STEPが LLM に返させる構造化出力の型。**mock経路では未使用＝P0bの実装シーム**。
JSON は camelCase（to_camel エイリアス）で授受し、Python 側は snake_case で扱う。
正本: docs/design/agent-io-contract.md ／ packages/prompts/*.md ／ eval/eval_set.yaml。
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Decision = Literal["approve", "revise"]
ThemeKind = Literal["honmei", "serendipity"]


class _Base(BaseModel):
    """camelCase エイリアス + フィールド名でも受け付ける共通設定（models.py と同方針）。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ── STEP1 読者分析: 3層 ReaderProfile（base 保持 / currentWork・readingBehavior 分析） ──
class ReaderBase(_Base):
    industry: str = ""
    job_type: str = ""
    position: str = ""
    org_scale: str = ""
    reading_genres: list[str] = Field(default_factory=list)


class UpcomingEvent(_Base):
    title: str
    date: str = ""


class EvidenceRef(_Base):
    claim: str
    source: str = ""


class ReaderCurrentWork(_Base):
    current_situation: str = ""
    active_work_themes: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    upcoming_key_events: list[UpcomingEvent] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ReaderBehavior(_Base):
    recent_reads: list[str] = Field(default_factory=list)
    highlights_summary: str = ""
    drop_signals: list[str] = Field(default_factory=list)
    feedback_summary: str = ""
    serendipity_tolerance: str = ""
    style_preference: str = ""


class ReaderProfile3Layer(_Base):
    base: ReaderBase = Field(default_factory=ReaderBase)
    current_work: ReaderCurrentWork = Field(default_factory=ReaderCurrentWork)
    reading_behavior: ReaderBehavior = Field(default_factory=ReaderBehavior)


# ── STEP2c 調査サブ×3（A 読者局面 / B 市場 / C テーマ知見） ──
class SubReaderContext(_Base):
    theme: str = ""
    pain_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class MarketFinding(_Base):
    title: str = ""
    point: str = ""
    source: str = ""


class SubMarket(_Base):
    theme: str = ""
    queries: list[str] = Field(default_factory=list)
    findings: list[MarketFinding] = Field(default_factory=list)
    market_gap: str = ""


class ThemeKeyPoint(_Base):
    point: str = ""
    source: str = ""


class SubThemeInsight(_Base):
    theme: str = ""
    key_points: list[ThemeKeyPoint] = Field(default_factory=list)


# ── STEP2b 企画担当者: PlanProposal（8項目） ──
class PlanProposal(_Base):
    proposal_id: Optional[str] = None
    theme_kind: Optional[ThemeKind] = None
    round: int = 1
    tentative_title: str
    reader_situation: str
    why_now_for_you: str
    core_message: str
    diff_from_market: str
    key_insights: list[str] = Field(default_factory=list)
    agenda_outline: list[str] = Field(default_factory=list)
    recommended_author_types: list[str] = Field(default_factory=list)


# ── STEP2a 企画リーダー: LeaderVerdict（4観点スコアゲート） ──
class LeaderScoreBreakdown(_Base):
    relevance: int = 0
    differentiation: int = 0
    research_use: int = 0
    title_hook: int = 0


class LeaderVerdict(_Base):
    round: int = 1
    score: int = 0
    score_breakdown: LeaderScoreBreakdown = Field(default_factory=LeaderScoreBreakdown)
    below_floor: bool = False
    decision: Decision = "revise"
    rejection_feedback: Optional[str] = None
    approved_plan: Optional[PlanProposal] = None


# ── STEP3 キャスティング: GeneratedPersonaSet（5人・voiceStyle×format 2軸） ──
class GeneratedPersona(_Base):
    persona_id: str
    name: str
    voice_style: str = ""
    format: str = ""
    persona: str = ""
    expertise: list[str] = Field(default_factory=list)
    past_books: list[str] = Field(default_factory=list)
    from_favorite: bool = False
    ephemeral: bool = True


class GeneratedPersonaSet(_Base):
    plan_id: Optional[str] = None
    theme_kind: Optional[ThemeKind] = None
    personas: list[GeneratedPersona] = Field(default_factory=list)
    reason: str = ""


# ── STEP4 著者プレビュー: BookDraft（7フィールド） ──
class AgendaEntry(_Base):
    chapter: str
    summary: str = ""


class BookDraft(_Base):
    book_id: Optional[str] = None
    title: str
    subtitle: str = ""
    delivery_reason: str = ""
    problem_to_solve: str = ""
    core_message: str = ""
    agenda: list[AgendaEntry] = Field(default_factory=list)
    preface_sample: str = ""


# ── STEP4 編集長プレビュー採点: EditorVerdict（プレビュー3観点） ──
class PreviewScoreBreakdown(_Base):
    raw_insight: int = 0
    persona_forward: int = 0
    catchiness: int = 0


class EditorVerdict(_Base):
    book_id: Optional[str] = None
    round: int = 1
    score: int = 0
    score_breakdown: PreviewScoreBreakdown = Field(default_factory=PreviewScoreBreakdown)
    decision: Decision = "revise"
    editor_feedback: Optional[str] = None


# ── モードB 編集長本文採点: BodyVerdict（本文ルーブリック5観点） ──
class BodyScoreBreakdown(_Base):
    coherence: int = 0
    hook: int = 0
    relevance: int = 0
    persona_consistency: int = 0
    actionability: int = 0


class BodyVerdict(_Base):
    score: int = 0
    score_breakdown: BodyScoreBreakdown = Field(default_factory=BodyScoreBreakdown)
    decision: Decision = "revise"
    weak_chapters: list[int] = Field(default_factory=list)
    editor_feedback: Optional[str] = None
