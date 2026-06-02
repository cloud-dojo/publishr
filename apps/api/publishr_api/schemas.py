"""APIリクエスト用スキーマ（フロントからは camelCase で届く）。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FeedbackInput(_Camel):
    read_percent: Optional[int] = None
    dropped: Optional[bool] = None
    rating: Optional[int] = None
    wants_sequel: Optional[bool] = None


class PipelineRunInput(_Camel):
    user_id: str = "u_tadokoro"
