"""モードB: 予約 → 執筆 → 入荷 の状態機械。

reserve_now: draft → reserved（同期・即時）
advance:     reserved → writing → published（非同期・タイマー）
本文は published 到達時に authoring ワーカーが生成して格納する。"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from typing import Optional

from publishr_schema import Book

from ..config import settings
from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from . import body_store

logger = logging.getLogger(__name__)

_CHARS_PER_MIN = 500  # 日本語のおおまかな読書速度（字/分）
_CHAPTER_RE = re.compile(r"(?m)^##\s")  # 本文の章見出し（## ）


def _body_chapter_count(body: str) -> int:
    """実本文の章数（## 見出しの数。見出しが無くても本文があれば1）。"""
    n = len(_CHAPTER_RE.findall(body or ""))
    return n if n else (1 if body else 0)


def _reading_minutes(body: str) -> int:
    """実本文の長さから読了目安（分）。"""
    return max(1, math.ceil(len(body) / _CHARS_PER_MIN)) if body else 0


def _body_preface(body: str, limit: int = 300) -> str:
    """序文サンプル＝実本文の冒頭プローズ（見出し行を除いた先頭段落を limit 字まで）。

    preview 段階の prefaceSample（別生成のティザー）が実本文とズレる問題を解消するため、
    入荷時に「実際に読む本文の書き出し」をサンプルに差し替える。
    """
    paras = [
        ln.strip()
        for ln in (body or "").split("\n")
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    text = "\n\n".join(paras)
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _persist_published(
    repo: RepositoryProtocol, book: Book, body: str, edit_round: int
) -> Book:
    """writing→published の永続化を1箇所に集約する（C3.3 オフロードのシーム）。

    既定（body_store=inline）は本文をドキュメントにそのまま持つ＝従来挙動（mock不変）。
    body_store=gcs のときだけ本文を非公開バケットへ退避し、ドキュメントには bodyUrl だけ残す。
    読了率は published 到達でリセットする（既存挙動）。
    推定分量(章数/分)と序文サンプルは **実本文から** 再計算して上書きする（preview の見積りや
    別生成ティザーと実体の乖離を解消＝「推定分量が違う」「序文と本文が異なる」を是正）。
    """
    fb = book.feedback.model_copy(update={"read_percent": 0})
    update: dict = {
        "status": "published",
        "edit_round": edit_round,
        "feedback": fb,
        "estimated_chapters": _body_chapter_count(body),
        "estimated_minutes": _reading_minutes(body),
    }
    preface = _body_preface(body)
    if preface:
        update["preface_sample"] = preface  # 実本文の書き出しに統一（空なら据え置き）
    store = body_store.get_body_store()
    if store is not None:
        update["body_url"] = store.put(book.id, body)
        update["body"] = ""  # 退避済み＝ドキュメントには本文を残さない（肥大防止）
    else:
        update["body"] = body  # inline（既定・従来挙動）
    return repo.upsert_book(book.model_copy(update=update))


def _generate_body(repo: RepositoryProtocol, book: Book) -> tuple[str, int]:
    """モードB 本文編集ループ（編集長⇄著者・最高3R）で本文を生成。(body, edit_round)。

    LLM は settings.publishr_llm（既定 mock＝決定的・課金ゼロ）。著者ペルソナは repo から引く
    （firestore の生成著者・fixtures の既定著者どちらも・無ければ mode_b 側で汎用著者に縮退）。
    rounds を使い切っても編集長が最終的に revise 判定のままの場合があり得る（実Vertexで確認済み）。
    現状はそれでも published にする（既存挙動を変えない）が、見逃さないよう warning ログを残す。
    """
    from publishr_agents.mode_b import write_body_loop  # noqa: PLC0415

    persona = repo.get_persona(book.author_persona_id)
    result = write_body_loop(
        book, persona=persona, rounds=settings.body_edit_rounds, llm=settings.publishr_llm
    )
    if result.body_verdict.get("decision") != "approve":
        logger.warning(
            "book %s published with unapproved body after %d edit round(s) "
            "(score=%s decision=%s weakChapters=%s)",
            book.id,
            result.edit_rounds,
            result.body_verdict.get("score"),
            result.body_verdict.get("decision"),
            result.body_verdict.get("weakChapters"),
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


def move_to_library(repo: RepositoryProtocol, book_id: str) -> Book:
    """入荷一覧から書庫へ移す（shelf="library"・動的フィルタリング）。

    入荷ビューは shelf=arrivals/odd を見るので shelf を library にすると一覧から外れ、
    書庫（status=published 全件・shelf 非依存）には残り続ける。status は変えない。
    所有者チェックは呼び出し側（router）が実施する（body エンドポイントと同方針）。
    """
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    return repo.upsert_book(book.model_copy(update={"shelf": "library"}))


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
    _persist_published(repo, book, body, edit_round)


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
    return _persist_published(repo, book, body, edit_round)
