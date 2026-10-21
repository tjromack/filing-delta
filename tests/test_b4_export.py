"""The Build 4 export (M9 gate): valid items pass; forged or malformed items are caught (needs data/sections)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "sections").exists(), reason="needs data/sections")


@pytest.fixture(scope="module")
def items():
    import export_b4
    return export_b4.build()


def errors(items):
    import export_b4
    return export_b4.validate(items)


def first(items, answerable):
    return next(i for i in items if i["label"]["answerable"] == answerable)


def test_the_export_is_valid_and_complete(items):
    assert len(items) == 60 and errors(items) == []
    assert sum(i["label"]["answerable"] for i in items) == 37
    assert {i["provenance"]["method"] for i in items} == {"jury_agreed", "human_adjudicated"}


def tamper(items, answerable, fn):
    bad = copy.deepcopy(first(items, answerable))
    fn(bad)
    return errors([bad])


@pytest.mark.parametrize("why,answerable,fn", [
    ("evidence text isn't the slice", True, lambda i: i["evidence"][0].update(text=i["evidence"][0]["text"] + " extra")),
    ("offsets moved", True, lambda i: i["evidence"][0].update(char_start=i["evidence"][0]["char_start"] + 1)),
    ("section hash changed", True, lambda i: i["evidence"][0].update(section_sha256="0" * 64)),
    ("answerable with no evidence", True, lambda i: i.update(evidence=[])),
    ("answerable with no gold answer", True, lambda i: i["label"].update(gold_answers=[])),
    ("unanswerable with evidence", False, "borrow"),
    ("malformed evidence entry", True, lambda i: i["evidence"].append({"cik": 1})),
    ("not an SEC URL", True, lambda i: i["evidence"][0].update(url="https://example.com/x")),
    ("unknown field", True, lambda i: i.update(extra=1)),
    ("bad id", False, lambda i: i.update(id="qa-1")),
    ("human-adjudicated without a human labeler", False,
     lambda i: i["provenance"].update(method="human_adjudicated")),
])
def test_forged_or_malformed_items_are_caught(items, why, answerable, fn):
    if fn == "borrow":              # a real, valid span attached to an unanswerable item
        real = copy.deepcopy(first(items, True)["evidence"][0])
        fn = lambda i: i["evidence"].append(real)          # noqa: E731
    assert tamper(items, answerable, fn), why
