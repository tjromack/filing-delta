"""Restatement context for a change (tie-break rule 3: "clearly restated elsewhere").

A change only shows one paragraph, but whether deleted text is really gone depends on the rest of the section. For
deleted (or inserted) passages of at least MIN_WORDS words, find the paragraph elsewhere on the other side that
contains most of those words, and show it to the classifier. Added and removed units get their closest counterpart,
the same context the labeling sheet shows. Deterministic; no model involved.
"""
from __future__ import annotations

from difflib import SequenceMatcher

MIN_WORDS = 12
MIN_COVERAGE = 0.6
CLOSEST_MIN = 0.2


def _coverage(passage: list[str], para: list[str]) -> float:
    if not passage:
        return 0.0
    m = sum(b.size for b in SequenceMatcher(None, passage, para, autojunk=False).get_matching_blocks())
    return m / len(passage)


def restatement_context(rec: dict, op: dict, old_text: str, new_text: str) -> dict | None:
    """rec: a diff record; op: one of its ops; old_text / new_text: the two full section texts."""
    ou = [(i, k, s, e) for i, (k, s, e) in enumerate(rec["old_units"]) if k == "paragraph"]
    nu = [(j, k, s, e) for j, (k, s, e) in enumerate(rec["new_units"]) if k == "paragraph"]
    a = " ".join(old_text[rec["old_units"][i][1]:rec["old_units"][i][2]] for i in op["old"]).split()
    b = " ".join(new_text[rec["new_units"][j][1]:rec["new_units"][j][2]] for j in op["new"]).split()
    status = op["status"]
    if status in ("added", "removed"):
        words, pool, side = (b, ou, "old") if status == "added" else (a, nu, "new")
        text = old_text if side == "old" else new_text
        best = max(((SequenceMatcher(None, words, text[s:e].split(), autojunk=False).ratio(), text[s:e])
                    for _, _, s, e in pool), default=(0.0, ""))
        if best[0] >= CLOSEST_MIN:
            return {"kind": "closest", "side": side, "similarity": round(best[0], 2), "text": best[1]}
        return None
    # Split/merged: the other part of the paragraph lives in a different unit; the same search finds it.
    if status not in ("reworded", "moved", "split", "merged") or not a or not b:
        return None
    deleted, inserted = [], []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("delete", "replace") and i2 - i1 >= MIN_WORDS:
            deleted.append(a[i1:i2])
        if tag in ("insert", "replace") and j2 - j1 >= MIN_WORDS:
            inserted.append(b[j1:j2])
    out = []
    for passages, pool, side, text, own in ((deleted, nu, "new", new_text, set(op["new"])),
                                            (inserted, ou, "old", old_text, set(op["old"]))):
        for passage in passages:
            best = max(((_coverage(passage, text[s:e].split()), text[s:e]) for idx, _, s, e in pool
                        if idx not in own), default=(0.0, ""))
            if best[0] >= MIN_COVERAGE:
                out.append({"side": side, "coverage": round(best[0], 2), "text": best[1],
                            "what": "deleted" if side == "new" else "inserted"})
    if not out:
        return None
    return {"kind": "restated", "passages": out}
