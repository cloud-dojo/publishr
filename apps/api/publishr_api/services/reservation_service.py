"""モードB: 予約 → 執筆 → 入荷 の状態機械。

reserve_now: draft → reserved（同期・即時）
advance:     reserved → writing → published（非同期・タイマー）
本文は published 到達時に authoring ワーカーが生成して格納する。"""

from __future__ import annotations

import asyncio
from typing import Optional

from publishr_schema import Book

from ..config import settings
from ..repositories.protocol import RepositoryProtocol


def _generate_body(repo: RepositoryProtocol, book: Book) -> tuple[str, int]:
    """モードB 本文編集ループ（編集長⇄著者・最高3R）で本文を生成。(body, edit_round)。

    LLM は settings.publishr_llm（既定 mock＝決定的・課金ゼロ）。著者ペルソナは repo から引く
    （firestore の生成著者・fixtures の既定著者どちらも・無ければ mode_b 側で汎用著者に縮退）。
    """
    from publishr_agents.mode_b import write_body_loop  # noqa: PLC0415

    persona = repo.get_persona(book.author_persona_id)
    result = write_body_loop(
        book, persona=persona, rounds=settings.body_edit_rounds, llm=settings.publishr_llm
    )
    return result.body, result.edit_rounds


def reserve_now(repo: RepositoryProtocol, book_id: str, *, owner_uid: str = "") -> Book:
    """draft→reserved を原子的に行う（同時最大cap冊・I-20）。

    count確認→条件付き遷移をリポジトリの `reserve_book_atomic` に委譲する（mock=ロック、
    firestore=transaction）。`owner_uid` 指定でその owner だけ数える（未指定は全体＝MVP単一）。
    存在しない=NotFoundError(404)／draft以外・cap超過=ConflictError(409)。
    """
    return repo.reserve_book_atomic(
        book_id,
        owner_uid=owner_uid,
        max_concurrent=settings.max_concurrent_reservations,
    )


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
    body, edit_round = _generate_body(repo, book)
    fb = book.feedback.model_copy(update={"read_percent": 0})
    repo.upsert_book(
        book.model_copy(
            update={"status": "published", "body": body, "edit_round": edit_round, "feedback": fb}
        )
    )


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
    body, edit_round = _generate_body(repo, book)
    fb = book.feedback.model_copy(update={"read_percent": 0})
    return repo.upsert_book(
        book.model_copy(
            update={"status": "published", "body": body, "edit_round": edit_round, "feedback": fb}
        )
    )
