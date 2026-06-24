"""執筆ジョブの Cloud Pub/Sub publish（QUEUE=pubsub 時のみ使用）。

`{bookId}` を JSON にしてトピックへ publish。worker（/api/worker/write）が push で受けて処理する。
google-cloud-pubsub は **この関数内で lazy import**（mock 経路・オフラインに依存を持ち込まない）。
"""

from __future__ import annotations

import json
import os

from ..config import settings


def _topic_path() -> str:
    from google.cloud import pubsub_v1  # noqa: PLC0415

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    return pubsub_v1.PublisherClient.topic_path(project, settings.pubsub_topic)


def publish_write_job(book_id: str) -> str:
    """執筆ジョブを Pub/Sub トピックへ publish。messageId を返す（同期・confirm 付き）。"""
    from google.cloud import pubsub_v1  # noqa: PLC0415

    publisher = pubsub_v1.PublisherClient()
    topic = _topic_path()
    data = json.dumps({"bookId": book_id}).encode("utf-8")
    future = publisher.publish(topic, data)
    return future.result(timeout=10)


def publish_planning_job(payload: dict) -> str:
    """企画ジョブ（{userId, owner, observeUid}）を企画トピックへ publish。messageId を返す。"""
    from google.cloud import pubsub_v1  # noqa: PLC0415

    publisher = pubsub_v1.PublisherClient()
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    topic = pubsub_v1.PublisherClient.topic_path(project, settings.pubsub_planning_topic)
    data = json.dumps(payload).encode("utf-8")
    future = publisher.publish(topic, data)
    return future.result(timeout=10)
