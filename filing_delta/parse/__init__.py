"""Section parser: bytes of a primary document in, one ParseResult per target section out (design doc §2)."""
from __future__ import annotations

from .blocks import flatten
from .locate import TARGETS, ParseResult, parse_filing


def parse_document(raw: bytes, form: str) -> dict[str, ParseResult]:
    return parse_filing(flatten(raw), form)


__all__ = ["TARGETS", "ParseResult", "parse_document"]
