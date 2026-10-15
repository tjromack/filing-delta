"""Model calls with recorded responses (FD-DEC 007): every request is keyed by a hash of its full body.

A recorded response is replayed instead of calling the API, so published numbers reproduce exactly without a key.
Sonnet 5.5 rejects non-default sampling settings, so recording is the only way to make its outputs repeatable.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DEFAULT_MODEL = "claude-sonnet-5-5"   # the one default (CLAUDE.md); everything else reads ANTHROPIC_MODEL


def model_id() -> str:
    return os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL


def request_key(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class OfflineMiss(RuntimeError):
    pass


class Provider(Protocol):
    def complete(self, request: dict) -> dict: ...


class AnthropicProvider:
    """messages.create with the request as given. Returns a plain, JSON-serialisable record."""

    def __init__(self) -> None:
        import truststore  # TLS-inspecting proxy on this machine (CLAUDE.md gotcha)

        truststore.inject_into_ssl()
        import anthropic

        self._client = anthropic.Anthropic()

    def complete(self, request: dict) -> dict:
        r = self._client.messages.create(**request)
        text = "".join(b.text for b in r.content if b.type == "text")
        usage = r.usage.to_dict() if hasattr(r.usage, "to_dict") else dict(r.usage)
        return {"id": r.id, "model": r.model, "stop_reason": r.stop_reason, "text": text, "usage": usage,
                "stop_details": r.stop_details.to_dict() if getattr(r, "stop_details", None) else None}


@dataclass
class Recorder:
    """Cache-first model access. offline=True never constructs a provider and fails on any miss."""

    cache_dir: Path
    offline: bool = False
    provider: Provider | None = None
    hits: int = 0
    calls: int = 0

    def _path(self, key: str) -> Path:
        return self.cache_dir / key[:2] / f"{key}.json"

    def complete(self, request: dict) -> tuple[dict, str]:
        key = request_key(request)
        p = self._path(key)
        if p.exists():
            self.hits += 1
            return json.loads(p.read_text(encoding="utf-8"))["response"], key
        if self.offline:
            raise OfflineMiss(f"no recorded response for request {key[:12]} (offline)")
        if self.provider is None:
            self.provider = AnthropicProvider()
        response = self.provider.complete(request)
        self.calls += 1
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".part")
        tmp.write_text(json.dumps({"request": request, "response": response}, sort_keys=True, ensure_ascii=False,
                                  indent=1), encoding="utf-8")
        os.replace(tmp, p)
        return response, key
