"""Golden boundaries on real filings (design §2.6).

These read the EDGAR cache, which isn't in git (it ships as a release artifact, M8). Without it they skip with a
reason rather than pass. Each entry is either human-confirmed or still proposed (see docs/golden-review.md); both
are enforced here, so any change to the parser's output on a golden filing is caught.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from filing_delta.edgar.cache import ResponseCache
from filing_delta.parse import parse_document
from filing_delta.parse.golden import words_sha256

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = json.loads((ROOT / "tests" / "golden" / "sections.json").read_text(encoding="utf-8"))
CACHE = ResponseCache(ROOT / "data" / "edgar-cache")


URLS = {r["accession"]: r["url"] for r in csv.DictReader((ROOT / "corpus" / "manifest.csv").open(encoding="utf-8"))}
_parsed: dict[str, dict] = {}


@pytest.mark.parametrize("entry", GOLDEN, ids=lambda e: f"{e['document']}:{e['section']}:{e['status']}")
def test_golden_section(entry):
    cached = CACHE.get(URLS[entry["accession"]])
    if cached is None:
        pytest.skip("EDGAR cache not present (run `filing-delta fetch`, or download the release cache)")
    if entry["accession"] not in _parsed:
        _parsed[entry["accession"]] = parse_document(cached.body, entry["form"])
    r = _parsed[entry["accession"]][entry["section"]]
    assert (r.outcome, r.form_kind) == (entry["outcome"], entry["form_kind"])
    assert len(r.text) == entry["chars"]
    assert (r.text[:120], r.text[-120:]) == (entry["head"], entry["tail"])
    assert r.sha256 == entry["sha256"]
    assert words_sha256(r.text) == entry["words_sha256"]


def test_golden_set_covers_every_archetype_and_outcome():
    kinds = {(e["outcome"], e["form_kind"]) for e in GOLDEN}
    assert {("ok", "full"), ("ok", "pointer"), ("ok", "absent"), ("failed", "pointer")} <= kinds
    reasons = {x for e in GOLDEN for x in e["reasons"]}
    assert {"followed_pointer", "anchor_only", "xref_index", "end_from_index_pages", "pointer_out",
            "item_omitted", "exhibit_incorporation"} <= reasons
    assert len({e["document"] for e in GOLDEN}) >= 12
