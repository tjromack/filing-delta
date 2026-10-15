"""Restatement context (tie-break rule 3), on a synthetic diff record."""
from __future__ import annotations

from filing_delta.classify.context import restatement_context

SUCCESSION = ("The Board has identified certain current managers who are capable of succeeding the Chief Executive "
              "Officer and has agreed on a replacement should one be needed")


def record(old_paras: list[str], new_paras: list[str]):
    def units(paras):
        text, us, pos = "", [], 0
        for p in paras:
            if text:
                text += "\n\n"
                pos += 2
            us.append(["paragraph", pos, pos + len(p)])
            text += p
            pos += len(p)
        return text, us
    to, ou = units(old_paras)
    tn, nu = units(new_paras)
    return {"old_units": ou, "new_units": nu}, to, tn


def test_deleted_passage_found_in_another_paragraph():
    old = ["Key personnel matter to us. " + SUCCESSION + ". Other text follows here as well.", "Unrelated risk."]
    new = ["Key personnel matter to us. Other text follows here as well.", "Unrelated risk.",
           "Succession: " + SUCCESSION + " today."]
    rec, to, tn = record(old, new)
    ctx = restatement_context(rec, {"status": "reworded", "old": [0], "new": [0]}, to, tn)
    assert ctx["kind"] == "restated"
    (p,) = ctx["passages"]
    assert p["what"] == "deleted" and p["side"] == "new" and p["text"].startswith("Succession:") and p["coverage"] >= 0.9


def test_genuinely_deleted_passage_gets_no_context():
    old = ["Key personnel matter to us. " + SUCCESSION + ". Other text follows here as well.", "Unrelated risk."]
    new = ["Key personnel matter to us. Other text follows here as well.", "Unrelated risk."]
    rec, to, tn = record(old, new)
    assert restatement_context(rec, {"status": "reworded", "old": [0], "new": [0]}, to, tn) is None


def test_the_changed_paragraph_itself_is_never_its_own_context():
    old = ["A " + SUCCESSION + "."]
    new = ["A " + SUCCESSION + ". And " + SUCCESSION + " again."]
    rec, to, tn = record(old, new)
    ctx = restatement_context(rec, {"status": "reworded", "old": [0], "new": [0]}, to, tn)
    assert ctx is None


def test_added_unit_gets_its_closest_old_paragraph():
    old = ["Climate change could cause hurricanes, floods and wildfires that produce losses affecting our businesses."]
    new = ["Climate change could cause or intensify hurricanes, floods and wildfires that may produce losses."]
    rec, to, tn = record(old, ["Unrelated."] + new)
    ctx = restatement_context(rec, {"status": "added", "old": [], "new": [1]}, to, tn)
    assert ctx["kind"] == "closest" and ctx["side"] == "old" and ctx["similarity"] >= 0.2
