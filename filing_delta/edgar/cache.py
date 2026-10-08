"""On-disk response cache keyed by URL. A warm cache means a re-run makes zero EDGAR requests (pin 1).

Layout: ``<root>/<host>/<sha[:2]>/<sha>.body`` plus ``<sha>.json`` (url, status, content type, body sha256).
Only 200 responses are cached. Writes are atomic (temp file + rename), so an interrupted run never leaves a
truncated body that a later run would trust.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CachedResponse:
    url: str
    body: bytes
    content_type: str


class ResponseCache:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _paths(self, url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        d = self.root / urlsplit(url).netloc / key[:2]
        return d / f"{key}.body", d / f"{key}.json"

    def get(self, url: str) -> CachedResponse | None:
        body_p, meta_p = self._paths(url)
        if not (body_p.exists() and meta_p.exists()):
            return None
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        body = body_p.read_bytes()
        if hashlib.sha256(body).hexdigest() != meta["sha256"]:
            raise CacheCorruption(f"cached body for {url} does not match its recorded sha256")
        return CachedResponse(url=url, body=body, content_type=meta.get("content_type", ""))

    def put(self, url: str, body: bytes, content_type: str) -> CachedResponse:
        body_p, meta_p = self._paths(url)
        body_p.parent.mkdir(parents=True, exist_ok=True)
        meta = {"url": url, "status": 200, "content_type": content_type,
                "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        _atomic_write(body_p, body)
        _atomic_write(meta_p, json.dumps(meta, indent=1, sort_keys=True).encode("utf-8"))
        return CachedResponse(url=url, body=body, content_type=content_type)


class CacheCorruption(RuntimeError):
    pass


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)
