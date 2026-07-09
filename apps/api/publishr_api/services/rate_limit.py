"""汎用レート制限（per-key 最小間隔・インメモリ・スレッド安全）— C4.9 公開API保護。

`TriggerGuard`（実行中ロック付き）より軽量＝最小間隔だけを見る。OAuth start/コールバック・
Drive フォルダ書込のように「短時間に連打する正当理由が無い」エンドポイントに掛ける。
予約(/reserve)は同時5冊cap(I-20)でコストを縛るため、複数冊を続けて予約する正当な操作を
妨げないよう、ここでは対象にしない。

注意（C4.9残）: インメモリ＝1プロセス内のみ。マルチインスタンス Cloud Run では共有ストア
（Firestore/Redis）が要る。state nonce 単回化（oauth_service.NonceStore）も同様。
"""

from __future__ import annotations

import threading


class RateLimitError(Exception):
    """レート制限超過。`status` はそのまま HTTP（429）へ写す。"""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class RateLimiter:
    def __init__(self, *, min_interval_sec: float) -> None:
        self._min = float(min_interval_sec)
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}

    def hit(self, key: str, *, now: float) -> None:
        """key の前回ヒットから min_interval 未満なら RateLimitError(429)。"""
        with self._lock:
            last = self._last.get(key)
            if last is not None and (now - last) < self._min:
                wait = self._min - (now - last)
                raise RateLimitError(429, f"レート制限: あと約{wait:.0f}秒お待ちください")
            # 期限切れキー（min_interval 経過）を掃除して肥大を防ぐ。
            for k in [k for k, t in self._last.items() if now - t >= self._min]:
                del self._last[k]
            self._last[key] = now

    def reset(self) -> None:
        """テスト・プロセス再初期化用に内部状態を空にする。"""
        with self._lock:
            self._last.clear()


def _auth_limiter() -> RateLimiter:
    from ..config import settings

    return RateLimiter(min_interval_sec=settings.auth_min_interval_sec)


# プロセス内で共有するリミッタ（C4.9）。テストは reset() で初期化する。
auth_limiter = _auth_limiter()
