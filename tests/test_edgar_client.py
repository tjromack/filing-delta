"""EDGAR client: fair-access behavior under a scripted network. No real HTTP, no real waiting."""
from __future__ import annotations

import random
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from filing_delta.edgar.client import (
    EdgarClient, Forbidden, NotFound, OfflineCacheMiss, RetriesExhausted, RetryPolicy, UserAgentRequired,
    parse_retry_after,
)
from filing_delta.edgar.ratelimit import RateLimiter

UA = "Test Runner test@example.com"
URL = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/doc.htm"


class FakeClock:
    """Monotonic time that only moves when someone sleeps."""

    def __init__(self) -> None:
        self.t = 1000.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        assert s >= 0
        self.sleeps.append(s)
        self.t += s


class Script:
    """A transport that replays a list of responses and records when each request arrived."""

    def __init__(self, clock: FakeClock, responses: list) -> None:
        self.clock = clock
        self.responses = list(responses)
        self.arrivals: list[float] = []
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.arrivals.append(self.clock.now())
        self.requests.append(request)
        r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r


def make(tmp_path, clock, script, **kw) -> EdgarClient:
    return EdgarClient(UA, tmp_path / "cache", transport=httpx.MockTransport(script), clock=clock.now,
                       wall_clock=lambda: 1_700_000_000.0, sleep=clock.sleep, rng=random.Random(0), **kw)


def ok(body: bytes = b"<html>ok</html>") -> httpx.Response:
    return httpx.Response(200, content=body, headers={"content-type": "text/html"})


def too_many(retry_after: str | None = None) -> httpx.Response:
    return httpx.Response(429, headers={"retry-after": retry_after} if retry_after else {})


# --- the declared User-Agent -------------------------------------------------------------------------------------

@pytest.mark.parametrize("ua", [None, "", "   ", "python-httpx/0.28", "Trevor Romack", "no-space@example.com"])
def test_refuses_to_start_without_a_declared_user_agent(tmp_path, ua):
    with pytest.raises(UserAgentRequired):
        EdgarClient(ua, tmp_path, transport=httpx.MockTransport(lambda r: ok()))


def test_every_request_carries_the_declared_user_agent(tmp_path):
    clock = FakeClock()
    script = Script(clock, [ok()])
    make(tmp_path, clock, script).get(URL)
    assert script.requests[0].headers["user-agent"] == UA


# --- the rate ceiling ---------------------------------------------------------------------------------------------

def test_rate_ceiling_is_never_exceeded(tmp_path):
    clock = FakeClock()
    script = Script(clock, [ok()])
    client = make(tmp_path, clock, script)
    for i in range(50):
        client.get(f"{URL}?n={i}")
    gaps = [b - a for a, b in zip(script.arrivals, script.arrivals[1:])]
    assert len(script.arrivals) == 50
    assert min(gaps) >= client.limiter.min_interval - 1e-9
    # And over any 1-second window there are never more than 5 requests (SEC allows 10).
    for i, start in enumerate(script.arrivals):
        assert sum(start <= t < start + 1.0 for t in script.arrivals[i:]) <= 5


def test_limiter_rejects_a_ceiling_above_secs_limit():
    with pytest.raises(ValueError):
        RateLimiter(max_per_second=11)


# --- the 429 storm ------------------------------------------------------------------------------------------------

def test_429_storm_backs_off_honors_retry_after_and_recovers(tmp_path):
    clock = FakeClock()
    script = Script(clock, [too_many("3"), too_many("3"), too_many(), too_many(), too_many("5"), ok(b"finally")])
    client = make(tmp_path, clock, script)

    assert client.get(URL).body == b"finally"
    assert len(script.arrivals) == 6
    assert client.stats.retries == 5

    gaps = [b - a for a, b in zip(script.arrivals, script.arrivals[1:])]
    assert gaps[0] >= 3 and gaps[1] >= 3          # Retry-After honored
    assert gaps[4] >= 5
    policy = RetryPolicy()
    for attempt, gap in enumerate(gaps):           # never sooner than the back-off floor (half the ceiling)
        assert gap >= min(policy.max_delay, policy.base_delay * 2 ** attempt) / 2 - 1e-9
    assert gaps[2] < gaps[3]                       # exponential growth where no Retry-After was given


def test_storm_pause_is_global_not_per_url(tmp_path):
    """After a 429 with Retry-After, the *next* URL also waits: the limiter is paused, not just the retry."""
    clock = FakeClock()
    script = Script(clock, [too_many("10"), ok(), ok()])
    client = make(tmp_path, clock, script)
    client.get(URL)
    client.get(URL + "?other")
    assert script.arrivals[1] - script.arrivals[0] >= 10
    assert script.arrivals[2] - script.arrivals[1] >= client.limiter.min_interval - 1e-9


def test_unending_storm_gives_up_and_caches_nothing(tmp_path):
    clock = FakeClock()
    script = Script(clock, [too_many()])
    client = make(tmp_path, clock, script, policy=RetryPolicy(max_attempts=4))
    with pytest.raises(RetriesExhausted):
        client.get(URL)
    assert len(script.arrivals) == 4
    assert client.cache.get(URL) is None


def test_absurd_retry_after_stops_instead_of_sleeping(tmp_path):
    clock = FakeClock()
    script = Script(clock, [too_many("86400")])
    with pytest.raises(RetriesExhausted, match="Retry-After"):
        make(tmp_path, clock, script).get(URL)
    assert clock.t < 1000.0 + 60


def test_5xx_and_transport_errors_are_retried(tmp_path):
    clock = FakeClock()
    req = httpx.Request("GET", URL)
    script = Script(clock, [httpx.Response(503), httpx.ConnectError("reset", request=req),
                            httpx.ReadTimeout("slow", request=req), ok()])
    client = make(tmp_path, clock, script)
    assert client.get(URL).body == b"<html>ok</html>"
    assert client.stats.retries == 3


def test_403_is_fatal_and_not_retried(tmp_path):
    clock = FakeClock()
    script = Script(clock, [httpx.Response(403)])
    with pytest.raises(Forbidden):
        make(tmp_path, clock, script).get(URL)
    assert len(script.arrivals) == 1


def test_404_raises_and_is_not_cached(tmp_path):
    clock = FakeClock()
    script = Script(clock, [httpx.Response(404)])
    client = make(tmp_path, clock, script)
    with pytest.raises(NotFound):
        client.get(URL)
    assert client.cache.get(URL) is None


def test_retry_after_http_date_form():
    now = datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)
    header = format_datetime(now + timedelta(seconds=30), usegmt=True)
    assert parse_retry_after(header, now.timestamp()) == pytest.approx(30)
    assert parse_retry_after("7", now.timestamp()) == 7
    assert parse_retry_after("garbage", now.timestamp()) is None


# --- the cache: a re-run costs zero requests ----------------------------------------------------------------------

def test_warm_cache_rerun_makes_zero_requests(tmp_path):
    clock = FakeClock()
    first = Script(clock, [ok(b"body")])
    make(tmp_path, clock, first).get(URL)

    second = Script(clock, [httpx.Response(500)])      # the network would fail if touched
    client = make(tmp_path, clock, second)
    assert client.get(URL).body == b"body"
    assert second.arrivals == []
    assert client.stats.network_requests == 0 and client.stats.cache_hits == 1


def test_offline_mode_never_touches_the_network(tmp_path):
    clock = FakeClock()
    script = Script(clock, [ok()])
    with pytest.raises(OfflineCacheMiss):
        make(tmp_path, clock, script, offline=True).get(URL)
    assert script.arrivals == []


def test_corrupted_cache_entry_is_detected(tmp_path):
    from filing_delta.edgar.cache import CacheCorruption

    clock = FakeClock()
    client = make(tmp_path, clock, Script(clock, [ok(b"original")]))
    client.get(URL)
    body_path = next((tmp_path / "cache").rglob("*.body"))
    body_path.write_bytes(b"tampered")
    with pytest.raises(CacheCorruption):
        client.get(URL)
