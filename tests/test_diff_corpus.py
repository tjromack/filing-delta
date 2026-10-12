"""Invariants over every real diff (needs data/: `filing-delta fetch`, `parse`, `diff`; skipped without it).

- Coverage: every unit on each side appears in at least one op. Nothing is silently dropped from a diff.
- Spans: every unit is an exact, non-empty span of its section's canonical text, and units don't overlap.
- Determinism: re-diffing a pair from the same inputs gives a byte-identical record.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from filing_delta.diff.run import _load, _text, diff_pair

ROOT = Path(__file__).resolve().parents[1]
SEC = ROOT / "data" / "sections"
FILES = sorted(glob.glob(str(ROOT / "data" / "diffs" / "*.json")))

pytestmark = pytest.mark.skipif(not FILES, reason="no diffs in data/ (run filing-delta fetch, parse, diff)")


def _records():
    for f in FILES:
        rec = json.loads(Path(f).read_text(encoding="utf-8"))
        if rec["state"] == "full -> full":
            yield f, rec


def test_every_unit_is_covered_by_an_op():
    for f, rec in _records():
        seen_old = {i for op in rec["ops"] for i in op["old"]}
        seen_new = {j for op in rec["ops"] for j in op["new"]}
        assert seen_old == set(range(len(rec["old_units"]))), f
        assert seen_new == set(range(len(rec["new_units"]))), f


def test_units_are_ordered_non_overlapping_spans():
    for f, rec in _records():
        for side in ("old", "new"):
            text = (SEC / rec[side]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
            prev_end = 0
            for kind, s, e in rec[f"{side}_units"]:
                assert prev_end <= s < e <= len(text), (f, side, s, e)
                assert text[s:e].strip() == text[s:e], (f, side, s)
                prev_end = e


def test_rediff_is_byte_identical():
    rows = {(r["accession"], r["section"]): r for r in _load(SEC)}
    checked = 0
    for f, rec in list(_records())[::25]:            # every 25th pair keeps this under a few seconds
        a = rows[(rec["old"]["accession"], rec["section"])]
        b = rows[(rec["new"]["accession"], rec["section"])]
        again = diff_pair(a, b, _text(SEC, a), _text(SEC, b))
        body = json.dumps(again, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        assert body == Path(f).read_text(encoding="utf-8"), f
        checked += 1
    assert checked >= 5
