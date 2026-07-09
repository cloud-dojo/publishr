"""執筆ジョブのキュー（`QUEUE=mock|pubsub` シーム）。

mock（既定）= in-process（`schedule_advance` のタイマーでデモUX・オフライン・課金ゼロ）。
pubsub = Cloud Pub/Sub のトピックへ `{bookId}` を publish し、worker（/api/worker/write）が消費。
クラウド依存（google-cloud-pubsub）は **pubsub 分岐の中だけ**（lazy import）に隔離する。
"""

from __future__ import annotations

from publishr_schema import Book

from ..config import settings
from ..repositories.protocol import RepositoryProtocol


def enqueue(repo: RepositoryProtocol, book_id: str) -> None:
    """予約された本の執筆ジョブを投入する（QUEUE 設定で mock/pubsub を切替）。"""
    if settings.queue == "pubsub":
        from .pubsub_queue import publish_write_job

        publish_write_job(book_id)
        return
    # mock（既定）: in-process でタイマー進行（reserved→writing→published）。
    from . import reservation_service

    reservation_service.schedule_advance(repo, book_id)


def reserve_and_enqueue(
    repo: RepositoryProtocol, book_id: str, *, owner_uid: str = ""
) -> Book:
    """予約（draft→reserved）→執筆ジョブ投入 を1単位で行い、投入失敗時は予約を巻き戻す。

    `enqueue`（pubsub なら publish_write_job）が失敗すると、再配信する元メッセージも無いまま本が
    reserved（=UI「準備中」）で滞留する。それを防ぐため publish 失敗時は `release_reservation` で
    draft へ戻してから例外を送出する（reserved 孤児を作らない）。予約自体の失敗（cap/conflict）は
    enqueue 前なので巻き戻し不要＝そのまま送出。mock 経路（enqueue=schedule_advance）は失敗しない
    ＝従来挙動（zero-diff）。
    """
    from . import reservation_service

    book = reservation_service.reserve_now(repo, book_id, owner_uid=owner_uid)
    try:
        enqueue(repo, book_id)
    except Exception:
        reservation_service.release_reservation(repo, book_id)
        raise
    return book


def enqueue_planning(
    repo: RepositoryProtocol,
    *,
    user_id: str,
    owner_uid: str,
    observe_uid: str | None,
    theme_kind: str = "honmei",
    run_id: str | None = None,
) -> bool:
    """企画ジョブ（モードA）を投入する。pubsub なら publish して True（非同期・即返し）。

    mock（既定）は in-process で即実行し False（＝同期実行済み・オフライン/テストは従来どおり
    決定的に本が作られる）。pubsub は worker（/api/worker/plan）が後で消費する。

    run_id（I-38）は **pubsub 経路のみ** payload に載せ、再配信時の冪等ロック/決定的ID に使う。
    mock 経路は run_id を mode_a_service.run へ渡さない＝従来動作（zero-diff）を厳守する。
    """
    if settings.queue == "pubsub":
        from .pubsub_queue import publish_planning_job

        payload = {"userId": user_id, "owner": owner_uid, "observeUid": observe_uid or "",
                   "themeKind": theme_kind}
        if run_id:
            payload["runId"] = run_id
        publish_planning_job(payload)
        return True
    from . import mode_a_service

    mode_a_service.run(repo, user_id, owner_uid=owner_uid, observe_uid=observe_uid,
                       theme_kind=theme_kind)
    return False
