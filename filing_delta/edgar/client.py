"""EDGAR HTTP client: declared User-Agent, rate ceiling, cache-first, back-off on 429/5xx (FD-DEC 004).

Every request goes through this one path: cache → rate limiter → network → retry policy → cache. The transport,
clock, sleep and RNG are injectable, so the 429-storm and rate-ceiling tests run with no network and no real waiting.
"""
from __future__ import annotations

import email.utils
import random
import re
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from .cache import CachedResponse, ResponseCache
from .ratelimit import RateLimiter

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_UA_RE = re.compile(r"^\S.*\s\S+@\S+\.\S+$")


class EdgarError(RuntimeError):
    pass


class UserAgentRequired(EdgarError):
    pass


class NotFound(EdgarError):
    pass


class Forbidden(EdgarError):
    """SEC answers 403 to undeclared or abusive clients. Never retried: retrying would make it worse."""


class RetriesExhausted(EdgarError):
    pass


class OfflineCacheMiss(EdgarError):
    pass


@dataclass
class RetryPolicy:
    max_attempts: int = 7
    base_delay: float = 1.0
    max_delay: float = 60.0
    max_retry_after: float = 600.0  # longer than this means something is wrong; stop instead of sleeping

    def backoff(self, attempt: int, rng: random.Random) -> float:
        """Exponential back-off with 'equal jitter': half fixed, half random, so the delay never collapses to ~0."""
        ceiling = min(self.max_delay, self.base_delay * (2 ** attempt))
        return ceiling / 2 + rng.uniform(0, ceiling / 2)


@dataclass
class Stats:
    network_requests: int = 0  # every attempt that touched the transport, including retries
    cache_hits: int = 0
    retries: int = 0
    slept_seconds: float = 0.0


def validate_user_agent(ua: str | None) -> str:
    if not ua or not _UA_RE.match(ua.strip()):
        raise UserAgentRequired(
            "EDGAR fair-access policy requires a declared User-Agent of the form 'Name email@domain'. "
            "Set EDGAR_USER_AGENT (see .env.example)."
        )
    return ua.strip()


def parse_retry_after(value: str | None, now_epoch: float) -> float | None:
    """Retry-After is either delta-seconds or an HTTP-date (RFC 9110 §10.2.3)."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, dt.timestamp() - now_epoch)


class EdgarClient:
    def __init__(
        self,
        user_agent: str | None,
        cache_dir: Path,
        *,
        transport: httpx.BaseTransport | None = None,
        limiter: RateLimiter | None = None,
        policy: RetryPolicy | None = None,
        offline: bool = False,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.user_agent = validate_user_agent(user_agent)
        self.cache = ResponseCache(cache_dir)
        self.limiter = limiter or RateLimiter(clock=clock, sleep=self._counted_sleep)
        self.policy = policy or RetryPolicy()
        self.offline = offline
        self.stats = Stats()
        self._clock = clock
        self._wall_clock = wall_clock
        self._sleep = sleep
        self._rng = rng or random.Random()
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        if transport is None:
            # The machine sits behind a TLS-inspecting proxy; verify against the OS trust store (CLAUDE.md gotcha).
            import truststore

            verify: ssl.SSLContext | bool = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self._http = httpx.Client(headers=headers, timeout=timeout, verify=verify, follow_redirects=True)
        else:
            self._http = httpx.Client(headers=headers, timeout=timeout, transport=transport, follow_redirects=True)

    def _counted_sleep(self, seconds: float) -> None:
        self.stats.slept_seconds += seconds
        self._sleep(seconds)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> EdgarClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, url: str) -> CachedResponse:
        cached = self.cache.get(url)
        if cached is not None:
            self.stats.cache_hits += 1
            return cached
        if self.offline:
            raise OfflineCacheMiss(f"offline mode and not cached: {url}")

        last_problem = ""
        for attempt in range(self.policy.max_attempts):
            self.limiter.acquire()
            self.stats.network_requests += 1
            try:
                resp = self._http.get(url)
            except httpx.TransportError as e:
                last_problem = f"{type(e).__name__}: {e}"
                retry_after = None
            else:
                if resp.status_code == 200:
                    return self.cache.put(url, resp.content, resp.headers.get("content-type", ""))
                if resp.status_code == 404:
                    raise NotFound(url)
                if resp.status_code == 403:
                    raise Forbidden(f"403 from EDGAR for {url}: check the User-Agent and the request rate")
                if resp.status_code not in RETRYABLE_STATUS:
                    raise EdgarError(f"HTTP {resp.status_code} for {url}")
                last_problem = f"HTTP {resp.status_code}"
                retry_after = parse_retry_after(resp.headers.get("retry-after"), self._wall_clock())

            if attempt == self.policy.max_attempts - 1:
                break
            if retry_after is not None and retry_after > self.policy.max_retry_after:
                raise RetriesExhausted(f"{url}: Retry-After {retry_after:.0f}s exceeds the {self.policy.max_retry_after:.0f}s limit")
            delay = self.policy.backoff(attempt, self._rng)
            if retry_after is not None:
                delay = max(delay, retry_after)
            self.stats.retries += 1
            # Pause the limiter itself, so the wait applies to every subsequent request, not just this URL.
            self.limiter.pause_until(self._clock() + delay)

        raise RetriesExhausted(f"{url}: gave up after {self.policy.max_attempts} attempts (last: {last_problem})")
