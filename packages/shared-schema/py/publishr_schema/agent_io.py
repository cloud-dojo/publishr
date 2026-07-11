"""Publishr v2 エージェントI/Oモデル（ADK output_schema 用・pydantic v2）。

モードA/Bの各STEPが LLM に返させる構造化出力の型。**mock経路では未使用＝P0bの実装シーム**。
JSON は camelCase（to_camel エイリアス）で授受し、Python 側は snake_case で扱う。
正本: packages/prompts/*.md ／ eval/eval_set.yaml。
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


# 週次インサイト（v3・棚の多様性設計の起点。STEP1が週1で出す）
class WeeklyInsight(_Base):
    overt_interests: list[str] = Field(default_factory=list)    # 顕在関心
    latent_interests: list[str] = Field(default_factory=list)   # 潜在関心
    cliche_to_avoid: list[str] = Field(default_factory=list)    # 回避したい陳腐さ
    emotional_tone: str = ""                                    # 今週の感情トーン
    desired_utility: list[str] = Field(default_factory=list)    # 求められる効用


class ReaderProfile3Layer(_Base):
    base: ReaderBase = Field(default_factory=ReaderBase)
    current_work: ReaderCurrentWork = Field(default_factory=ReaderCurrentWork)
    reading_behavior: ReaderBehavior = Field(default_factory=ReaderBehavior)
    weekly_insight: WeeklyInsight = Field(default_factory=WeeklyInsight)  # ★v3


# ── STEP2c 調査サブ×3（v3＝テーマ非依存・器は流用／A 人物深掘り / B 業界トレンド / C 直近売れ筋本） ──
class SubReaderContext(_Base):  # A 人物深掘り（theme は任意・テーマ非依存）
    theme: str = ""
    pain_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    interests_map: list[str] = Field(default_factory=list)  # ★v3: 関心の地図（テーマ候補の素材）
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


# ── STEP2c-1 トレンドリサーチャー（今・時間軸・v3 4テーマ）。market＝SubMarket／普遍＝SubThemeInsight と対 ──
class TrendPoint(_Base):
    point: str = ""   # 「最近こう変わった/こう動いている」時間軸の事実
    source: str = ""  # grounding 出典URL


class SubTrendInsight(_Base):
    theme: str = ""
    queries: list[str] = Field(default_factory=list)
    trends: list[TrendPoint] = Field(default_factory=list)
    era_shift: str = ""  # 潮流の根（何が変わって今の関心になったか）


# ── STEP2-0 編集意図（編集長・棚コンセプト＋制約・v3） ──
class EditorialIntent(_Base):
    shelf_concept: str = ""          # 今週の棚コンセプト（世界観）
    reader_experience: str = ""      # 読後体験
    anti_duplication: list[str] = Field(default_factory=list)     # 似た本を避けるルール
    balance_constraints: list[str] = Field(default_factory=list)  # バランス制約


# ── STEP2 テーマ群（4テーマ 1-1-1-1・役割つき・v3） ──
class ThemeSpec(_Base):
    theme_id: Optional[str] = None
    name: str
    role: str = ""               # 主軸 | 実務補助 | 視座替え | 回復・内省 等（例示・自由文字列）
    target_reader: str = ""      # 想定読者
    value: str = ""              # 提供価値
    forbidden_overlap: str = ""  # 禁止重複条件


# ── STEP2-0 編集長テーマ設定（4チームA/B/Dに1サブテーマずつ割当・v3）。出力＝ThemeAssignmentSet ──
class ThemeAssignment(_Base):
    team_id: str = ""                 # A | B | C | D
    theme: ThemeSpec                  # 割り当てたサブテーマ


class ThemeAssignmentSet(_Base):
    theme_kind: Optional[ThemeKind] = None
    editorial_intent: Optional[EditorialIntent] = None
    assignments: list[ThemeAssignment] = Field(default_factory=list)  # 4チーム＝4テーマ


# ── STEP2b 企画担当者: PlanProposal（企画書8項目＋配本属性5・v3） ──
class PlanProposal(_Base):
    proposal_id: Optional[str] = None
    theme_kind: Optional[ThemeKind] = None
    round: int = 1
    # ── 配本属性（v3・4テーマ 1-1-1-1。多様性4軸＝theme/bookRole/utility/emotionalTone） ──
    theme: str = ""              # どのテーマか（ThemeSpec.name）
    theme_role: str = ""         # 主力 | 準主力 | 実験
    book_role: str = ""          # 形式: ハンドブック/ケース・ストーリー/哲学・内省/具体ノウハウ/感情エッセイ/対話・問答 等
    utility: str = ""            # 効用: 学べる/癒える/勇気が出る/視点が変わる 等
    emotional_tone: str = ""     # 感情トーン: 厳しい/優しい/熱い/静か/不穏 等
    target_segment: str = ""     # 読者セグメント
    # ── 企画書フレーム8項目 ──
    tentative_title: str
    reader_situation: str
    why_now_for_you: str
    core_message: str
    diff_from_market: str
    key_insights: list[str] = Field(default_factory=list)
    agenda_outline: list[str] = Field(default_factory=list)
    recommended_author_types: list[str] = Field(default_factory=list)


# ── STEP2 配本セット（4テーマ→1-1-1-1で4冊・v3） ──
class PlanSet(_Base):
    theme_kind: Optional[ThemeKind] = None
    editorial_intent: Optional[EditorialIntent] = None
    themes: list[ThemeSpec] = Field(default_factory=list)    # 4テーマ
    plans: list[PlanProposal] = Field(default_factory=list)  # 4冊（1-1-1-1）
    allocation: str = "1-1-1-1"
    portfolio_reason: str = ""


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


# ── STEP2a ポートフォリオゲート: PlanSetVerdict（5冊をセット採点・v3） ──
class PerPlanScore(_Base):
    plan_id: Optional[str] = None
    score: int = 0
    score_breakdown: LeaderScoreBreakdown = Field(default_factory=LeaderScoreBreakdown)
    below_floor: bool = False
    decision: Decision = "revise"


class PortfolioScore(_Base):
    axis_spread: int = 0          # 多様性4軸の分散数（最低3軸でバラける）
    constraints_ok: bool = False  # 配本制約（同テーマ/セグメント/形式 最大2冊・同トーン連続2冊）充足
    intent_alignment: int = 0     # 編集意図との整合（0〜25）
    allocation_ok: bool = False   # 1-1-1-1 充足（4テーマ各1冊）


class PlanSetVerdict(_Base):
    round: int = 1
    per_plan: list[PerPlanScore] = Field(default_factory=list)
    portfolio: PortfolioScore = Field(default_factory=PortfolioScore)
    score: int = 0                # セット総合
    decision: Decision = "revise"
    rejection_feedback: Optional[str] = None
    approved_plans: Optional[list[PlanProposal]] = None


# ── STEP3 キャスティング: GeneratedPersonaSet（v3＝4冊それぞれに1著者・著者間非重複） ──
class GeneratedPersona(_Base):
    persona_id: str
    plan_id: Optional[str] = None  # ★v3: 担当する冊（PlanProposal.proposalId）
    name: str
    voice_style: str = ""
    format: str = ""
    persona: str = ""
    expertise: list[str] = Field(default_factory=list)
    past_books: list[str] = Field(default_factory=list)
    from_favorite: bool = False
    ephemeral: bool = True


class GeneratedPersonaSet(_Base):
    plan_id: Optional[str] = None   # 対象企画（PlanProposal.proposalId）
    theme_kind: Optional[ThemeKind] = None
    personas: list[GeneratedPersona] = Field(default_factory=list)  # 4人（1人/冊）
    reason: str = ""


# ── STEP3 著者キャスティング（v3・4テーマ）: AuthorCasting（1企画＝3候補生成→1人選抜・選抜証跡） ──
# チームリーダーが承認企画ごとに架空著者3候補を生成し最適1人を chosen に選ぶ。GeneratedPersonaSet（1コール集合）とは別形。
class AuthorCasting(_Base):
    plan_id: Optional[str] = None                                      # 対象企画（PlanProposal.proposalId）
    candidates: list[GeneratedPersona] = Field(default_factory=list)   # 候補3人（voiceStyle×format×価値の核で散らす）
    chosen: Optional[GeneratedPersona] = None                          # 選抜した1人（candidates の personaId と一致）
    selection_reason: str = ""                                         # なぜ他候補でなくこれか（書店で見える証跡）


# ── セレンディピティ: 別ロジック（隣接/反対/飛躍/ニッチで4テーマ→4冊・v3） ──
class SerendipityTheme(_Base):
    theme_id: Optional[str] = None
    name: str
    adjacency: str = ""          # 隣接 | 反対 | 飛躍 | ニッチ（例示・自由文字列）
    why_for_reader: str = ""     # なぜ今この読者に出すのか（薄く）


class SerendipitySet(_Base):
    themes: list[SerendipityTheme] = Field(default_factory=list)  # 4テーマ→4冊
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
