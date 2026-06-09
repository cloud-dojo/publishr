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


_ACTIVE_STATUSES = ("reserved", "writing")


def _active_count(repo: RepositoryProtocol) -> int:
    """同時進行中（reserved+writing）の冊数。firestore では owner スコープで数える。"""
    return sum(len(repo.list_books(status=s)) for s in _ACTIVE_STATUSES)


def reserve_now(repo: RepositoryProtocol, book_id: str) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    if book.status != "draft":
        raise ConflictError(f"予約できません（現在の状態: {book.status}）")
    # 同時最大5冊（I-16）。モードBの実行コストを天井留めする。
    # NOTE(I-20): mock/単一プロセスでは「数えて→予約」で十分。本番の並行予約の原子性は
    # Firestore transaction（count確認→条件付き遷移）で別途担保する（firestore ハードニング）。
    cap = settings.max_concurrent_reservations
    if _active_count(repo) >= cap:
        raise ConflictError(f"同時に予約できるのは最大{cap}冊までです（予約中の本を読み終えてから）")
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


def process_write_job(repo: RepositoryProtocol, book_id: str) -> Optional[Book]:
    """執筆ジョブを **冪等** に処理する（Pub/Sub worker / 再配信の共通入口）。

    予約済み(reserved)→writing→published＋本文 を即時（タイマー無し）で進める。二重配信されても
    published/その他状態は再処理しない（I-20）。本文生成器の差し替え（mode_b）は別軸（C2.3）。
    """
    book = repo.get_book(book_id)
    if book is None:
        return None
    if book.status not in ("reserved", "writing"):
        return book  # 既に処理済み or 予約外 → skip（冪等）
    if book.status == "reserved":
        book = repo.upsert_book(book.model_copy(update={"status": "writing"}))
    body = write_body(book)
    fb = book.feedback.model_copy(update={"read_percent": 0})
    return repo.upsert_book(
        book.model_copy(update={"status": "published", "body": body, "feedback": fb})
    )
