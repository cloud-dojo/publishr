"""読書中の表示粒度・ハイライト・付箋の反映。"""

from __future__ import annotations

from publishr_schema import Book, ReadingAnnotation

from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from ..schemas import ReadingStateInput
from .feedback_service import sanitize_text

_ANNOTATION_TEXT_MAX = 500  # schema 上限と同値。保存時の防御的サニタイズ（制御文字除去）と対。


def apply_reading_state(repo: RepositoryProtocol, book_id: str, payload: ReadingStateInput) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")

    updates: dict[str, object] = {}
    if payload.granularity is not None:
        updates["granularity"] = payload.granularity
    if payload.annotations is not None:
        # annotations の text/note は untrusted（学習ループが読者分析へ抜粋する）。
        # 制御文字を除去して保存する（長さ上限は schema 側で 422）。
        updates["annotations"] = [
            ReadingAnnotation.model_validate(
                {
                    **annotation.model_dump(),
                    "text": sanitize_text(annotation.text, _ANNOTATION_TEXT_MAX) or "",
                    "note": sanitize_text(annotation.note, _ANNOTATION_TEXT_MAX),
                }
            )
            for annotation in payload.annotations
        ]
    return repo.upsert_book(book.model_copy(update=updates))
