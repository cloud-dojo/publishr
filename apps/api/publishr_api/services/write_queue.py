"""執筆ジョブのキュー（`QUEUE=mock|pubsub` シーム）。

mock（既定）= in-process（`schedule_advance` のタイマーでデモUX・オフライン・課金ゼロ）。
pubsub = Cloud Pub/Sub のトピックへ `{bookId}` を publish し、worker（/api/worker/write）が消費。
クラウド依存（google-cloud-pubsub）は **pubsub 分岐の中だけ**（lazy import）に隔離する。
"""

from __future__ import annotations

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
