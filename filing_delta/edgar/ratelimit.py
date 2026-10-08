"""A minimum-interval rate limiter with an injectable clock, so the ceiling can be asserted in tests."""
from __future__ import annotations

import time
from collections.abc import Callable

# SEC's fair-access ceiling is 10 requests/second. We run at half that (FD-DEC 004).
DEFAULT_MAX_PER_SECOND = 5.0


class RateLimiter:
    """Spaces request starts at least ``1 / max_per_second`` apart, and can be paused (e.g. after a 429)."""

    def __init__(
        self,
        max_per_second: float = DEFAULT_MAX_PER_SECOND,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not 0 < max_per_second <= 10:
            raise ValueError("max_per_second must be in (0, 10]: SEC's fair-access ceiling is 10 req/s")
        self.min_interval = 1.0 / max_per_second
        self._clock = clock
        self._sleep = sleep
        self._next_allowed = float("-inf")

    def acquire(self) -> float:
        """Block until a request may start; returns the start time it granted."""
        now = self._clock()
        if now < self._next_allowed:
            self._sleep(self._next_allowed - now)
            now = self._clock()
        self._next_allowed = now + self.min_interval
        return now

    def pause_until(self, t: float) -> None:
        """No request may start before ``t`` (used to honor Retry-After globally)."""
        self._next_allowed = max(self._next_allowed, t)
