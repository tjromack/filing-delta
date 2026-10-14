"""The aligner against Trevor's 70 labeled pairs (instance criterion; FD-DEC 018). Needs data/; skipped without it.

Holds the published numbers as a floor: a change to segmentation or alignment that lowers precision or recall on
the labeled pairs fails here. An improvement passes, and then the published numbers should be regenerated
(`python tools/eval_alignment.py`).

This reads the stored diffs in data/diffs, so it checks code changes only after `filing-delta diff` has been re-run.
That is the pipeline order: fetch → parse → diff → test, and the clean-clone run (M8) follows it. Re-diffing the
35 labeled filing pairs inside the test would add ~40 s to every run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

PUBLISHED_PRECISION = 0.83
PUBLISHED_RECALL = 0.80

pytestmark = pytest.mark.skipif(not (ROOT / "data" / "diffs").exists(), reason="no diffs in data/")


def test_aligner_meets_published_precision_and_recall():
    import eval_alignment as ev

    sample = json.loads((ROOT / "tests" / "golden" / "alignment_sample.json").read_text(encoding="utf-8"))
    lab = ev.labels()
    items = [{**m, "label": lab[m["id"]]} for m in sample["items"] if lab.get(m["id"]) in ("Y", "N")]
    assert len(items) == 70
    ev.as_run(items)
    assert not [i["id"] for i in items if i["as_run"] == "unmapped"]
    p, r, _, _ = ev.score(items, sample["population"],
                          lambda i: i["as_run"] in ("unchanged", "reworded", "moved", "split", "merged"))
    assert round(p, 2) >= PUBLISHED_PRECISION, p
    assert round(r, 2) >= PUBLISHED_RECALL, r
