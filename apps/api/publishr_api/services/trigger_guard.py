"""手動トリガー（POST /api/trigger/planning）のガード。

C4前ゲートの一部: 許可uid・レート制限・実行中ロックをインメモリで提供する。
時刻は `now`（単調増加秒・例: time.monotonic()）を注入して決定的にテストできる。
スレッド安全（FastAPI の sync エンドポイントはスレッドプールで動くため）。
"""

from __future__ import annotations

import threading
from collections.abc import Iterable


class TriggerError(Exception):
    """トリガー拒否。`status` はそのまま HTTP ステータスへ写す。"""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class TriggerGuard:
    """uid 単位の許可・レート制限・多重起動防止。

    - allowed_uids が空なら全許可（dev）。非空なら allowlist のみ。
    - min_interval_sec 未満の連打は 429。
    - 実行中（acquire 後 release 前）の同 uid 再取得は 409。
    """

    def __init__(self, *, min_interval_sec: float, allowed_uids: Iterable[str]) -> None:
        self._min = float(min_interval_sec)
        self._allowed = {u for u in allowed_uids if u}
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}
        self._running: set[str] = set()

    def acquire(self, uid: str, *, now: float) -> None:
        with self._lock:
            if self._allowed and uid not in self._allowed:
                raise TriggerError(403, "このユーザーはトリガーを実行できません")
            if uid in self._running:
                raise TriggerError(409, "企画パイプラインが実行中です。完了までお待ちください")
            last = self._last.get(uid)
            if last is not None and (now - last) < self._min:
                wait = self._min - (now - last)
                raise TriggerError(429, f"レート制限: あと約{wait:.0f}秒お待ちください")
            self._running.add(uid)

    def release(self, uid: str, *, now: float) -> None:
        with self._lock:
            self._running.discard(uid)
            self._last[uid] = now

    def reset(self) -> None:
        """テスト・プロセス再初期化用に内部状態を空にする。"""
        with self._lock:
            self._last.clear()
            self._running.clear()
