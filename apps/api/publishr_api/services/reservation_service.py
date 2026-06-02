"""モードB: 予約 → 執筆 → 入荷 の状態機械。

reserve_now: draft → reserved（同期・即時）
advance:     reserved → writing → published（非同期・タイマー）
本文は published 到達時に authoring ワーカーが生成して格納する。"""

from __future__ import annotations

import asyncio
from typing import Optional

from publishr_agents import write_body
from publishr_schema import Book

from ..config import settings
from ..errors import ConflictError, NotFoundError
from ..repositories.protocol import RepositoryProtocol


def reserve_now(repo: RepositoryProtocol, book_id: str) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    if book.status != "draft":
        raise ConflictError(f"予約できません（現在の状態: {book.status}）")
    return repo.upsert_book(book.model_copy(update={"status": "reserved"}))


async def advance(
    repo: RepositoryProtocol,
    book_id: str,
    t1: Optional[float] = None,
    t2: Optional[float] = None,
) -> None:
    """reserved → writing → published をタイマーで進める。"""
    t1 = settings.reserve_to_writing_sec if t1 is None else t1
    t2 = settings.writing_to_published_sec if t2 is None else t2

    await asyncio.sleep(t1)
    book = repo.get_book(book_id)
    if book is None or book.status != "reserved":
        return
    repo.upsert_book(book.model_copy(update={"status": "writing"}))

    await asyncio.sleep(t2)
    book = repo.get_book(book_id)
    if book is None or book.status != "writing":
        return
    body = write_body(book)
    fb = book.feedback.model_copy(update={"read_percent": 0})
    repo.upsert_book(book.model_copy(update={"status": "published", "body": body, "feedback": fb}))


def schedule_advance(repo: RepositoryProtocol, book_id: str) -> None:
    """イベントループ上に状態遷移タスクを登録（async エンドポイントから呼ぶ）。"""
    asyncio.create_task(advance(repo, book_id))
