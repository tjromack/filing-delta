"""M0 research fetcher: pulls a hand-picked sample of EDGAR documents for the section-parser design.

Not the M1 client. It shells out to curl (OS trust store; see the proxy gotcha in CLAUDE.md), sends the declared
User-Agent from .env, sleeps between requests (well under SEC's 10 req/s), and caches every response under
data/m0/ so a re-run makes zero requests.

    python tools/m0_fetch.py URL [URL ...]      # prints the cache path for each URL
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "m0"
MIN_INTERVAL_S = 0.5  # <= 2 req/s


def user_agent() -> str:
    ua = os.environ.get("EDGAR_USER_AGENT")
    env = ROOT / ".env"
    if not ua and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("EDGAR_USER_AGENT="):
                ua = line.split("=", 1)[1].strip().strip('"')
    if not ua or "@" not in ua:
        sys.exit("EDGAR_USER_AGENT must be set ('Name email') — EDGAR fair-access policy.")
    return ua


def cache_path(url: str) -> Path:
    name = url.rstrip("/").rsplit("/", 1)[-1] or "index"
    return CACHE / f"{hashlib.sha256(url.encode()).hexdigest()[:12]}_{name}"


_last = 0.0


def fetch(url: str, ua: str) -> Path:
    global _last
    path = cache_path(url)
    if path.exists():
        return path
    wait = MIN_INTERVAL_S - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    r = subprocess.run(
        ["curl", "-sS", "--compressed", "-A", ua, "-o", str(tmp), "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    _last = time.monotonic()
    if r.stdout.strip() != "200":
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"HTTP {r.stdout.strip()} for {url} {r.stderr.strip()}")
    tmp.rename(path)
    return path


if __name__ == "__main__":
    ua = user_agent()
    for u in sys.argv[1:]:
        print(fetch(u, ua))
