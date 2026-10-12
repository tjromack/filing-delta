"""Comparison keys (design §2.4: the comparison key is separate from the canonical text).

`key` treats typography as equal: Unicode compatibility forms, curly vs. straight quotes, dash variants and
whitespace. Two units with the same key are *unchanged*, whatever quote style the filer agent used that year.
`loose_key` also ignores case and punctuation. Units that differ only under `key` but match under `loose_key` are
reported as reworded with the fact `formatting_only`. That is a deterministic observation, not a materiality call.
"""
from __future__ import annotations

import re
import unicodedata

_QUOTES = str.maketrans({"‘": "'", "’": "'", "ʼ": "'", "′": "'", "‚": "'", "“": '"', "”": '"', "″": '"', "„": '"'})
_DASHES = re.compile(r"[‐‑‒–—―−]")
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:[.,]\d+)*%?|\$|%")


def key(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    t = _DASHES.sub("-", t)
    return _WS.sub(" ", t).strip()


def loose_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", key(text).lower())


def tokens(text: str) -> list[str]:
    """Words and numbers, lowercased. Used for similarity and for word-level change facts."""
    return [t.lower() for t in _TOKEN.findall(key(text))]
