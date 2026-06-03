"""Publishr の共有データモデル（pydantic v2）。

フィクスチャ/API/Firestore で同一スキーマを保つための単一の型定義。
フィールドは Python 慣習の snake_case で定義し、JSON 入出力は camelCase
（`to_camel` エイリアス）で扱う。"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

BookStatus = Literal["draft", "reserved", "writing", "published"]
Shelf = Literal["arrivals", "press", "odd", "library"]
Granularity = Literal["full", "summary", "excerpt"]


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


class User(_Base):
    id: str
    name: str
    initial: str
    profile: UserProfile


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


class Plan(_Base):
    id: str
    reason: str
    core_message: str
    reader_situation: str
    differentiator: str = ""
    agenda_outline: list[str] = Field(default_factory=list)
    recommended_author_types: list[str] = Field(default_factory=list)


class Observation(_Base):
    note_count: int = 0
    top_labels: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)


class ReaderProfile(_Base):
    role: str = ""
    situation: str = ""
    interests: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    serendipity_tolerance: str = ""


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
    feedback: Feedback = Field(default_factory=Feedback)
