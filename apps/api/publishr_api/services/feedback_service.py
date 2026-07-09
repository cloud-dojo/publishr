"""読後フィードバックの反映（★評価・続編希望・読了率・自由記述感想など）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from publishr_schema import Book

from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from ..schemas import FeedbackInput

_IMPRESSION_MAX = 2000  # 自由記述感想の保存上限（文字）
_REACTION_MAX = 200  # readingReaction（"good:<理由>" 等）の保存上限（文字）
# 制御文字を除去（改行・タブは残す）。プロンプトインジェクション対策の入口の基本サニタイズ。
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: Optional[str], max_len: int) -> Optional[str]:
    """untrusted テキストを保存用に整える: 制御文字除去＋上限カット。中身の意味解釈はしない（保存のみ）。
    LLM へ渡すのは別工程（Stage 2）で正規化してから＝ここは『安全に貯める』だけ。"""
    if text is None:
        return None
    cleaned = _CTRL_RE.sub("", text).strip()
    return cleaned[:max_len]


def _sanitize_impression(text: Optional[str]) -> Optional[str]:
    return sanitize_text(text, _IMPRESSION_MAX)


def apply_feedback(repo: RepositoryProtocol, book_id: str, payload: FeedbackInput) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    updates = payload.model_dump(exclude_unset=True)
    # 読了率の更新＝読書イベント。最後に読んだ時刻をサーバ側で刻む（「最近読んだ本」の並び順）。
    # クライアント送信値は信用せず、read_percent が来たら常にサーバ時刻で上書きする。
    if updates.get("read_percent") is not None:
        updates["last_read_at"] = datetime.now(timezone.utc).isoformat()
    # 自由記述感想/reaction は untrusted。保存時に制御文字除去＋長さ制限する
    # （生文を LLM に渡すのは Stage 2 で正規化後）。
    if "impression" in updates:
        updates["impression"] = _sanitize_impression(updates["impression"])
    if "reading_reaction" in updates:
        updates["reading_reaction"] = sanitize_text(updates["reading_reaction"], _REACTION_MAX)
    new_feedback = book.feedback.model_copy(update=updates)
    return repo.upsert_book(book.model_copy(update={"feedback": new_feedback}))
