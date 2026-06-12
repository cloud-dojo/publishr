"""C4.9 汎用レート制限（RateLimiter）の単体テスト（決定的・now 注入）。"""

from __future__ import annotations

import pytest
from publishr_api.services.rate_limit import RateLimiter, RateLimitError


def test_blocks_within_min_interval():
    rl = RateLimiter(min_interval_sec=3.0)
    rl.hit("k", now=100.0)
    with pytest.raises(RateLimitError) as ei:
        rl.hit("k", now=101.0)  # 1秒後＝3秒未満
    assert ei.value.status == 429


def test_allows_after_interval():
    rl = RateLimiter(min_interval_sec=3.0)
    rl.hit("k", now=100.0)
    rl.hit("k", now=103.0)  # ちょうど3秒後＝許可


def test_keys_are_independent():
    rl = RateLimiter(min_interval_sec=3.0)
    rl.hit("a", now=100.0)
    rl.hit("b", now=100.0)  # 別キーは干渉しない


def test_reset_clears_state():
    rl = RateLimiter(min_interval_sec=3.0)
    rl.hit("k", now=100.0)
    rl.reset()
    rl.hit("k", now=100.5)  # reset 後は直後でも許可
