"""APIリクエスト用スキーマ（フロントからは camelCase で届く）。"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FeedbackInput(_Camel):
    read_percent: Optional[int] = None
    dropped: Optional[bool] = None
    rating: Optional[int] = None
    wants_sequel: Optional[bool] = None


class ReadingAnnotationInput(_Camel):
    id: str
    kind: Literal["highlight", "note", "bookmark"]
    paragraph_index: int
    text: str
    note: Optional[str] = None


class ReadingStateInput(_Camel):
    granularity: Optional[Literal["full", "summary", "excerpt"]] = None
    annotations: Optional[list[ReadingAnnotationInput]] = None


class PipelineRunInput(_Camel):
    user_id: str = "u_tadokoro"
