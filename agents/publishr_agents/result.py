"""パイプラインの出力型。"""

from __future__ import annotations

from typing import Literal

from publishr_schema import Book, Observation, Plan, ReaderProfile
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Verdict = Literal["採用", "却下", "保留"]


class _Base(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RejectLogEntry(_Base):
    """企画会議の採否ログ1件。round=1 で全却下→再提出、round=2 で採否確定。"""

    round: int
    candidate: str
    persona: str
    verdict: Verdict
    reason: str


class PipelineResult(_Base):
    plans: list[Plan] = Field(default_factory=list)
    books: list[Book] = Field(default_factory=list)
    observation: Observation = Field(default_factory=Observation)
    reader_profile: ReaderProfile = Field(default_factory=ReaderProfile)
    reject_log: list[RejectLogEntry] = Field(default_factory=list)
