"""APIリクエスト用スキーマ（フロントからは camelCase で届く）。"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FeedbackInput(_Camel):
    read_percent: Optional[int] = None
    dropped: Optional[bool] = None
    rating: Optional[int] = None
    wants_sequel: Optional[bool] = None
    reading_reaction: Optional[str] = None


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
    user_id: str = "u_sakura"


class ReserveInput(_Camel):
    book_id: str


class TriggerPlanningInput(_Camel):
    user_id: str = "u_sakura"


class DriveFolderLabelInput(_Camel):
    folder_id: str
    label: str = ""


class DriveFoldersInput(_Camel):
    """Drive Picker（C1.1.2・鉄田 UI）が選んだフォルダIDをサーバ保存するための入力。

    観測は folderId ごとに Drive クエリを1本投げる（N+1）ため、件数を上限で抑える
    （quota/コスト暴走防止）。folderId 自体の形式検証はルータ（不正文字=400）で行う。
    """

    folder_ids: list[str] = Field(max_length=50)
    labels: Optional[list[DriveFolderLabelInput]] = Field(default=None, max_length=50)
