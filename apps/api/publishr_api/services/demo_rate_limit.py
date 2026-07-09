"""デモ公開のライブ生成レートガード（②G）。

匿名公開で実 Vertex 生成を晒すため、**グローバル日次上限**と **client 単位の日次上限**を強制する。
TriggerGuard（uid 単位・連打/多重防止・インメモリ）では足りない理由:
  - 匿名は全員 demo_uid に集約されるため per-anon の区別ができない → client_id で数える。
  - Cloud Run は minInstances=0 でアイドル時にインスタンスが落ちる → インメモリ日次カウンタは
    リセットされ「日次上限」が効かない → 本番は Firestore 永続ストア（インスタンス跨ぎで正しい）。

ストアは原子的に「上限内なら +1、超過なら拒否」する責務を持つ（read→check→write の競合を防ぐ）。
テスト/mock は `InMemoryDemoRateStore`、本番は `FirestoreDemoRateStore`。
"""

from __future__ import annotations

import threading
from typing import Protocol


class DemoRateError(Exception):
    """日次上限超過。HTTP 429 を返す。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.status = 429
        self.message = message


class DemoRateStore(Protocol):
    """日次レートの永続化＋原子的予約。"""

    def reserve(self, *, day: str, client_id: str, global_cap: int, per_client_cap: int) -> None:
        """`day` の global 合計と client 個別を原子的にチェックし、上限内なら両方 +1。

        global 合計が `global_cap` 以上、または client 個別が `per_client_cap` 以上なら
        `DemoRateError` を送出し、カウンタは増やさない（超過リクエストで枠を消費しない）。
        """
        ...


class InMemoryDemoRateStore:
    """インメモリ実装（テスト/単一プロセス用）。本番は Firestore 版を使う。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total: dict[str, int] = {}
        self._client: dict[tuple[str, str], int] = {}

    def reserve(self, *, day: str, client_id: str, global_cap: int, per_client_cap: int) -> None:
        with self._lock:
            total = self._total.get(day, 0)
            cc = self._client.get((day, client_id), 0)
            if total >= global_cap:
                raise DemoRateError(
                    "本日の体験枠（全体）が上限に達しました。また明日お試しください。"
                )
            if cc >= per_client_cap:
                raise DemoRateError(
                    "本日のあなたの体験枠が上限に達しました。また明日お試しください。"
                )
            self._total[day] = total + 1
            self._client[(day, client_id)] = cc + 1


class DemoRateLimiter:
    """日次のグローバル＋client 上限を強制する。`day` は呼び出し側が注入（決定的テスト）。"""

    def __init__(self, *, store: DemoRateStore, global_cap: int, per_client_cap: int) -> None:
        self._store = store
        self._global_cap = int(global_cap)
        self._per_client_cap = int(per_client_cap)

    @property
    def enabled(self) -> bool:
        # 上限 0 以下は「無効（全許可）」＝ローカル/mock の従来挙動を壊さない。
        return self._global_cap > 0 and self._per_client_cap > 0

    def acquire(self, client_id: str, *, day: str) -> None:
        if not self.enabled:
            return
        self._store.reserve(
            day=day,
            client_id=client_id or "anon",
            global_cap=self._global_cap,
            per_client_cap=self._per_client_cap,
        )

    # client_id 無しの trigger（Scheduler/直叩き curl）の計数バケット。
    _SERVER_CLIENT_ID = "__server__"

    def acquire_server(self, *, day: str) -> None:
        """client_id が無い呼び出しにも global 日次上限を課す（バイパス封じ・P0ハードニング）。

        per-client 枠は global と同値にして実質無効化＝Scheduler/運用の複数回実行を
        per-client 3 で縛らない。消費は global に合算（別勘定にしない）。
        """
        if not self.enabled:
            return
        self._store.reserve(
            day=day,
            client_id=self._SERVER_CLIENT_ID,
            global_cap=self._global_cap,
            per_client_cap=self._global_cap,
        )


class FirestoreDemoRateStore:
    """本番（実GCP）: Firestore トランザクションで日次カウンタを原子的に予約する。

    doc `demo_rate/{YYYY-MM-DD}` に `{total: int, clients: {clientId: int}}`。
    minInstances=0 でインスタンスが落ちても日次状態が残る（インスタンス跨ぎで正しい）。
    """

    _COLL = "demo_rate"

    def __init__(self) -> None:
        from ..repositories.firestore_repository import _ensure_initialized  # noqa: PLC0415

        _ensure_initialized()
        from firebase_admin import firestore as fb_firestore  # noqa: PLC0415

        self._db = fb_firestore.client()
        self._fs = fb_firestore

    def reserve(self, *, day: str, client_id: str, global_cap: int, per_client_cap: int) -> None:
        ref = self._db.collection(self._COLL).document(day)

        @self._fs.transactional
        def _txn(transaction) -> None:  # type: ignore[no-untyped-def]
            snap = ref.get(transaction=transaction)
            data = snap.to_dict() or {}
            total = int(data.get("total", 0))
            clients = dict(data.get("clients", {}) or {})
            cc = int(clients.get(client_id, 0))
            if total >= global_cap:
                raise DemoRateError(
                    "本日の体験枠（全体）が上限に達しました。また明日お試しください。"
                )
            if cc >= per_client_cap:
                raise DemoRateError(
                    "本日のあなたの体験枠が上限に達しました。また明日お試しください。"
                )
            clients[client_id] = cc + 1
            transaction.set(ref, {"total": total + 1, "clients": clients})

        _txn(self._db.transaction())


def get_demo_rate_limiter() -> DemoRateLimiter:
    """設定からレートリミッタを構築（プロセス内で1回・api.py が保持）。

    caps が 0 なら無効（全許可）＝mock/local 非破壊。firestore モードのみ Firestore 永続、
    それ以外（mock/test）はインメモリ。
    """
    from ..config import settings  # noqa: PLC0415

    g = settings.demo_rate_global_cap
    c = settings.demo_rate_per_client_cap
    store: DemoRateStore
    if g > 0 and c > 0 and settings.data_source == "firestore":
        store = FirestoreDemoRateStore()
    else:
        store = InMemoryDemoRateStore()
    return DemoRateLimiter(store=store, global_cap=g, per_client_cap=c)
