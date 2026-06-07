"""Publishr の共有データモデル（pydantic v2）。

フィクスチャ/API/Firestore で同一スキーマを保つための単一の型定義。
フィールドは Python 慣習の snake_case で定義し、JSON 入出力は camelCase
（`to_camel` エイリアス）で扱う。

正本:
  - エージェント I/O: docs/design/agent-io-contract.md
  - API 境界:        docs/design/api-contract.md
  - Firestore ルール: docs/design/firestore-security-rules.md
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

BookStatus = Literal["draft", "reserved", "writing", "published"]
Shelf = Literal["arrivals", "press", "odd", "library"]
Granularity = Literal["full", "summary", "excerpt"]
AnnotationKind = Literal["highlight", "note", "bookmark"]
ThemeKind = Literal["honmei", "serendipity"]
Decision = Literal["approve", "revise"]


class _Base(BaseModel):
    """camelCase エイリアス + フィールド名でも受け付ける共通設定。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChecklistItem(_Base):
    text: str
    checked: bool = False


class KeepNote(_Base):
    id: str
    user_id: str
    title: str
    text: str
    labels: list[str] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    pinned: bool = False
    updated_at: str


class UserProfile(_Base):
    role: str
    work_theme: str
    estimated_interests: list[str] = Field(default_factory=list)
    serendipity_tolerance: str


# ---------------------------------------------------------------------------
# api-contract.md §2-a: ユーザー登録時の初期プロフィール（Firestore 直書き）
# ---------------------------------------------------------------------------
class InitialProfile(_Base):
    industry: str
    job_type: str
    position: str
    recent_interests: list[str] = Field(default_factory=list)
    reading_genres: list[str] = Field(default_factory=list)
    created_at: str = ""
    skipped: bool = False


# ---------------------------------------------------------------------------
# tech-architecture.md §3: connectedSources（観測ソース接続・3ソース）
# Google Picker でフォルダ単位選択した folderIds[] をサーバ保持（G1-13）。
# ---------------------------------------------------------------------------
class DriveFolderLabel(_Base):
    """Picker で選んだフォルダへの業務/趣味ラベル（folderLabel の由来）。"""
    folder_id: str
    label: str = ""  # "業務" | "趣味"


class DriveConnection(_Base):
    enabled: bool = True
    folder_ids: list[str] = Field(default_factory=list)
    labels: list[DriveFolderLabel] = Field(default_factory=list)


class CalendarConnection(_Base):
    enabled: bool = True
    calendar_ids: list[str] = Field(default_factory=list)


class TasksConnection(_Base):
    enabled: bool = True


class ConnectedSources(_Base):
    """STEP0 観測の入力＝どのソース/フォルダを読むか。drive は folderIds 配下のみ。"""
    drive: Optional[DriveConnection] = None
    calendar: Optional[CalendarConnection] = None
    tasks: Optional[TasksConnection] = None


class User(_Base):
    id: str
    name: str
    initial: str
    profile: UserProfile
    # api-contract.md §2-a / §3-a 追加フィールド
    initial_profile: Optional[InitialProfile] = None
    favorite_authors: list[dict[str, Any]] = Field(default_factory=list)
    # favorite_authors 各要素: {personaId, name, voiceStyle, format, savedAt}
    # tech-architecture.md §3: 観測ソース接続（STEP0 の入力）
    connected_sources: Optional[ConnectedSources] = None


class PastBook(_Base):
    book_id: str
    title: str
    user_rating: int


class PersonaDetail(_Base):
    career: str
    style_note: str
    thought: str
    signature: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


class Persona(_Base):
    id: str
    name: str
    name_reading: str
    monogram: str
    style: str
    title: str
    persona: PersonaDetail
    expertise: list[str] = Field(default_factory=list)
    past_books: list[PastBook] = Field(default_factory=list)
    # agent-io-contract.md §5-3a 追加フィールド
    voice_style: str = ""       # narrative axis（文体軸）
    format: str = ""            # writing format（形式軸）
    from_favorite: bool = False # お気に入り著者由来か（15% 混入ロジック）
    ephemeral: bool = True      # 毎回生成される著者（永続しない）


class Plan(_Base):
    id: str
    reason: str
    core_message: str
    reader_situation: str
    differentiator: str = ""
    agenda_outline: list[str] = Field(default_factory=list)
    recommended_author_types: list[str] = Field(default_factory=list)
    # agent-io-contract.md §4-2b (PlanProposal) 追加フィールド
    proposal_id: str = ""
    theme_kind: ThemeKind | str = ""     # "honmei" | "serendipity"
    round: int = 0
    tentative_title: str = ""
    why_now_for_you: str = ""
    diff_from_market: str = ""           # 正本名（differentiator は後方互換で残す）
    key_insights: list[str] = Field(default_factory=list)


class Observation(_Base):
    note_count: int = 0
    top_labels: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# agent-io-contract.md §3: ReaderProfile 3 層構造
# ---------------------------------------------------------------------------
class ReaderProfileBase(_Base):
    """STEP1 読者分析: 基本属性層。"""
    industry: str = ""
    job_type: str = ""
    position: str = ""
    org_scale: str = ""
    reading_genres: list[str] = Field(default_factory=list)


class ReaderProfileCurrentWork(_Base):
    """STEP1 読者分析: 現在の仕事状況層。"""
    current_situation: str = ""
    active_work_themes: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)
    upcoming_key_events: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ReaderProfileReadingBehavior(_Base):
    """STEP1 読者分析: 読書傾向層。"""
    recent_reads: list[dict[str, Any]] = Field(default_factory=list)
    highlights_summary: str = ""
    drop_signals: list[dict[str, Any]] = Field(default_factory=list)
    feedback_summary: str = ""
    serendipity_tolerance: str = ""
    style_preference: str = ""


class ReaderProfile(_Base):
    # 既存フラット構造（後方互換）
    role: str = ""
    situation: str = ""
    interests: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    serendipity_tolerance: str = ""
    # agent-io-contract.md §3: 3 層構造（エージェント実装側で使う）
    base: Optional[ReaderProfileBase] = None
    current_work: Optional[ReaderProfileCurrentWork] = None
    reading_behavior: Optional[ReaderProfileReadingBehavior] = None


class PlanningCandidate(_Base):
    key: str
    persona: str
    candidate: str
    plan_id: Optional[str] = None


class AgendaItem(_Base):
    no: str
    title: str
    desc: str
    locked: bool = False
    note: Optional[str] = None


class Feedback(_Base):
    read_percent: int = 0
    dropped: bool = False
    rating: Optional[int] = None
    wants_sequel: bool = False
    reading_reaction: Optional[str] = None


class ReadingAnnotation(_Base):
    id: str
    kind: AnnotationKind
    paragraph_index: int
    text: str
    note: Optional[str] = None


# ===========================================================================
# 以下: agent-io-contract.md 由来の新規モデル（エージェント I/O 専用）
# ===========================================================================

# ---------------------------------------------------------------------------
# STEP0: ObservationBundle（§2）
# ---------------------------------------------------------------------------
class DriveFile(_Base):
    file_id: str
    name: str
    mime_type: str
    folder_label: str = ""
    text_excerpt: str = ""
    modified_time: str


class CalendarEvent(_Base):
    title: str
    start: str
    end: str
    attendees_count: int = 0
    recurring: bool = False


class TaskItem(_Base):
    title: str
    due: Optional[str] = None
    status: str = "needsAction"
    notes: str = ""


class ReadingHighlight(_Base):
    book_id: str
    text: str
    created_at: str


class ReadingLog(_Base):
    book_id: str
    read_percent: int
    dropped: bool = False
    dwell_sec: int = 0


class SimpleFeedback(_Base):
    book_id: str
    rating: int
    wants_sequel: bool = False


class DriveSource(_Base):
    files: list[DriveFile] = Field(default_factory=list)


class CalendarSource(_Base):
    events: list[CalendarEvent] = Field(default_factory=list)


class TasksSource(_Base):
    items: list[TaskItem] = Field(default_factory=list)


class ReadingFeedbackRef(_Base):
    """readingFB.feedback 要素（§2）。ReadingLog と SimpleFeedback の集約形。"""
    book_id: str
    rating: int = 0
    wants_sequel: bool = False
    read_percent: float = 0.0
    dropped: bool = False


class ReadingFB(_Base):
    highlights: list[ReadingHighlight] = Field(default_factory=list)
    feedback: list[ReadingFeedbackRef] = Field(default_factory=list)


class ObservationBundle(_Base):
    """STEP0 非エージェントツールの出力。Drive/Calendar/Tasks を束ねる（§2）。"""
    user_id: str
    collected_at: str
    drive: DriveSource = Field(default_factory=DriveSource)
    calendar: CalendarSource = Field(default_factory=CalendarSource)
    tasks: TasksSource = Field(default_factory=TasksSource)
    # to_camel だと readingFb になるため、契約 §2 の readingFB に明示矯正
    reading_fb: ReadingFB = Field(default_factory=ReadingFB, alias="readingFB")


# ---------------------------------------------------------------------------
# STEP2a: LeaderVerdict（§4-2a）企画リーダーの採点・差し戻し
# ---------------------------------------------------------------------------
class LeaderScoreBreakdown(_Base):
    relevance: int = 0         # 0-25: 読者との関連性
    differentiation: int = 0   # 0-25: 差別化
    research_use: int = 0      # 0-25: 調査活用度
    title_hook: int = 0        # 0-25: タイトルの引き


class LeaderVerdict(_Base):
    """STEP2a 企画リーダーが返す採点結果。score >= 70 で approve。"""
    round: int
    score: int
    score_breakdown: LeaderScoreBreakdown = Field(default_factory=LeaderScoreBreakdown)
    below_floor: bool = False
    decision: Decision
    rejection_feedback: Optional[str] = None
    approved_plan: Optional[dict[str, Any]] = None  # PlanProposal を dict で保持


# ---------------------------------------------------------------------------
# STEP2c: Research サブエージェント出力（§4-2c）
# ---------------------------------------------------------------------------
class SubReaderContext(_Base):
    """調査サブA: 読者コンテキスト（Drive/Tasks/Calendar由来）。"""
    pain_points: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class SubMarket(_Base):
    """調査サブB: 市場・競合調査（Google 検索 grounding）。"""
    theme_kind: str = ""
    queries: list[str] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    market_gap: str = ""


class SubThemeInsight(_Base):
    """調査サブC: テーマ知見（Google 検索 grounding）。"""
    key_points: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# STEP4: EditorVerdict（§5-2b）編集長の採点・差し戻し
# ---------------------------------------------------------------------------
class EditorScoreBreakdown(_Base):
    raw_insight: int = 0      # 0-34: 生の洞察
    persona_forward: int = 0  # 0-33: ペルソナの前進
    catchiness: int = 0       # 0-33: 引きの強さ


class EditorVerdict(_Base):
    """STEP4 編集長が返す採点結果。score >= 75 で approve（1 ラウンドのみ）。"""
    book_id: str
    round: int
    score: int
    score_breakdown: EditorScoreBreakdown = Field(default_factory=EditorScoreBreakdown)
    decision: Decision
    editor_feedback: Optional[str] = None


# ---------------------------------------------------------------------------
# Book（本体）
# ---------------------------------------------------------------------------
class Book(_Base):
    id: str
    plan_id: str
    status: BookStatus
    author_persona_id: str
    title: str
    subtitle: str = ""
    cover_variant: str
    cover_url: Optional[str] = None
    shelf: Shelf
    estimated_chapters: int = 0
    estimated_minutes: int = 0
    granularity: Granularity = "full"
    preface_sample: str = ""
    agenda: list[AgendaItem] = Field(default_factory=list)
    body: Optional[str] = None
    annotations: list[ReadingAnnotation] = Field(default_factory=list)
    feedback: Feedback = Field(default_factory=Feedback)
    # agent-io-contract.md §5-2a (BookDraft) 追加フィールド
    owner_uid: str = ""             # Firestore セキュリティルールの根幹
    kind: ThemeKind | str = ""      # "honmei" | "serendipity"
    delivery_reason: str = ""       # 書店 UI「入荷理由」表示に使用
    problem_to_solve: str = ""      # 本詳細画面: 解決する課題
    core_message: str = ""          # 本詳細画面: 核心メッセージ
    edit_round: int = 0             # 編集ループ回数
    body_url: Optional[str] = None  # GCS 本文 URL（Mode B 完了後に付与）
    created_at: str = ""            # 入荷日時（ISO8601）
