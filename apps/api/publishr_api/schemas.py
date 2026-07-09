"""APIリクエスト用スキーマ（フロントからは camelCase で届く）。"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FeedbackInput(_Camel):
    # 範囲検証は表示崩し対策（BookCard は「★×rating」を描く）＋ untrusted 入力の境界（P0ハードニング）。
    read_percent: Optional[int] = Field(default=None, ge=0, le=100)
    dropped: Optional[bool] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    wants_sequel: Optional[bool] = None
    # schema 上限は DoS 境界。保存時にさらにサニタイズ＋200字カット（feedback_service）。
    reading_reaction: Optional[str] = Field(default=None, max_length=2000)
    last_read_at: Optional[str] = Field(default=None, max_length=64)  # 通常は読了率更新時にサーバ側で自動付与
    impression: Optional[str] = Field(
        default=None, max_length=20_000
    )  # 自由記述感想（サーバで2000字制限/サニタイズして保存）


class ReadingAnnotationInput(_Camel):
    # 長さ上限は「巨大 annotations が GET /books で全訪問者へ毎回配信される」肥大攻撃の境界。
    # UI のハイライトは48字スライス済みなので通常操作には影響しない。
    id: str = Field(max_length=100)
    kind: Literal["highlight", "note", "bookmark"]
    paragraph_index: int = Field(ge=0, le=100_000)
    text: str = Field(max_length=500)
    note: Optional[str] = Field(default=None, max_length=500)


class ReadingStateInput(_Camel):
    granularity: Optional[Literal["full", "summary", "excerpt"]] = None
    annotations: Optional[list[ReadingAnnotationInput]] = Field(default=None, max_length=200)


class PipelineRunInput(_Camel):
    user_id: str = "u_sakura"


class ReserveInput(_Camel):
    book_id: str


class TriggerPlanningInput(_Camel):
    user_id: str = "u_sakura"
    theme_kind: str = "honmei"
    # I-38: 安定 run_id（任意）。未指定なら API 側で生成。手動検証で再配信冪等を試すために受け取る。
    # Firestore ドキュメントID になるため長さを制限（禁止文字・予約パターンは repo 側 _safe_doc_id で無害化）。
    run_id: Optional[str] = Field(default=None, max_length=256)
    # ②G デモ公開: 無認証ライブ生成のレート計数単位（クライアント発行UUID）。
    # あり＝per-client 上限も課す。無し（Scheduler/直叩き）も global 日次上限は課される
    # （P0ハードニング: client_id 省略によるキャップバイパスを塞いだ）。
    client_id: Optional[str] = Field(default=None, max_length=100)


class DriveFolderLabelInput(_Camel):
    folder_id: str
    label: str = ""


class DriveFoldersInput(_Camel):
    """Drive Picker（C1.1.2・フロント担当 UI）が選んだフォルダIDをサーバ保存するための入力。

    観測は folderId ごとに Drive クエリを1本投げる（N+1）ため、件数を上限で抑える
    （quota/コスト暴走防止）。folderId 自体の形式検証はルータ（不正文字=400）で行う。
    """

    folder_ids: list[str] = Field(max_length=50)
    labels: Optional[list[DriveFolderLabelInput]] = Field(default=None, max_length=50)
