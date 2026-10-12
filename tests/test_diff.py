"""M3 diff: segmentation, keys, alignment statuses, determinism. Pure functions, synthetic inputs."""
from __future__ import annotations

from filing_delta.diff.align import align
from filing_delta.diff.normalize import key, loose_key, tokens
from filing_delta.diff.segment import segment


def doc(*paras: str, tables: dict[int, list[list[str]]] | None = None) -> tuple[str, list[tuple]]:
    """Canonical text + block map, built the way the parser builds them ('\\n\\n' between blocks)."""
    text, bmap, pos, row = "", [], 0, 0
    tables = tables or {}
    for k, p in enumerate(paras):
        if k in tables:
            for r in tables[k]:
                row += 1
                for cell in r:
                    if text:
                        text += "\n\n"
                        pos += 2
                    bmap.append((pos, pos + len(cell), len(bmap), 1000 + k, row))
                    text += cell
                    pos += len(cell)
            continue
        if text:
            text += "\n\n"
            pos += 2
        bmap.append((pos, pos + len(p), len(bmap), None, None))
        text += p
        pos += len(p)
    return text, bmap


def run(old: list[str], new: list[str]):
    to, bo = doc(*old)
    tn, bn = doc(*new)
    uo, un = segment(to, bo), segment(tn, bn)
    return align(to, uo, tn, un), uo, un


P = [f"Risk factor number {i} describes how {w} could adversely affect our business, results of operations and "
     f"financial condition in ways that are difficult to predict and may be significant." for i, w in
     enumerate(["competition", "regulation", "cybersecurity incidents", "supply chain disruption", "interest rates",
                "litigation", "climate events", "labor shortages"])]


def statuses(ops):
    return [(op.status, op.old, op.new) for op in ops]


# --- keys --------------------------------------------------------------------------------------------------------

def test_key_folds_typography_but_not_words():
    assert key("Management’s “discussion” — 2025") == key("Management's \"discussion\" - 2025")
    assert key("a  b c") == "a b c"
    assert key("revenue rose") != key("revenue fell")


def test_loose_key_ignores_case_and_punctuation():
    assert loose_key("RISK FACTORS.") == loose_key("Risk factors")
    assert tokens("Net sales of $1,234.5 million, up 12%") == ["net", "sales", "of", "$", "1,234.5", "million", "up", "12%"]


# --- segmentation ---------------------------------------------------------------------------------------------------

def test_data_table_is_one_unit_layout_rows_are_not():
    text, bmap = doc("Results of operations improved.", "TABLE",
                     tables={1: [["Net sales", "2025", "2024"], ["Total", "994", "812"]]})
    units = segment(text, bmap)
    assert [u.kind for u in units] == ["paragraph", "table"]
    assert text[units[1].start:units[1].end].startswith("Net sales") and text[units[1].start:units[1].end].endswith("812")


def test_bullet_glyph_joins_its_text():
    text, bmap = doc("•", "Ability of the Firm to maintain the security of its systems.")
    units = segment(text, bmap)
    assert len(units) == 1 and units[0].kind == "paragraph"


def test_units_are_exact_spans_of_the_canonical_text():
    text, bmap = doc(*P[:3], "Strategic Risks")
    for u in segment(text, bmap):
        assert text[u.start:u.end] in text and u.key == key(text[u.start:u.end])
    assert [u.kind for u in segment(text, bmap)] == ["paragraph"] * 3 + ["heading"]


# --- alignment statuses ---------------------------------------------------------------------------------------------

def test_identical_sections_are_all_unchanged():
    ops, _, _ = run(P, P)
    assert {op.status for op in ops} == {"unchanged"} and len(ops) == len(P)


def test_typography_only_change_is_unchanged():
    curly = [p.replace("our", "our’s") for p in P[:2]]
    straight = [p.replace("our", "our's") for p in P[:2]]
    ops, _, _ = run(curly, straight)
    assert {op.status for op in ops} == {"unchanged"}


def test_added_removed_reworded():
    old = P[:5]
    new = [P[0], P[1].replace("difficult to predict", "difficult to predict or mitigate, particularly in 2025"),
           P[3], P[4], "We are newly exposed to tariffs imposed on imported components, which could raise our costs "
                       "and reduce demand for our products in several important markets."]
    ops, _, _ = run(old, new)
    got = statuses(ops)
    assert ("reworded", [1], [1]) in got
    assert ("removed", [2], []) in got
    assert ("added", [], [4]) in got
    assert sum(s == "unchanged" for s, _, _ in got) == 3


def test_moved_paragraph():
    old = P[:6]
    new = [P[0], P[2], P[3], P[4], P[5], P[1]]
    ops, _, _ = run(old, new)
    assert ("moved", [1], [5]) in statuses(ops)
    assert sum(op.status == "unchanged" for op in ops) == 5


def test_in_order_skeleton_covers_the_most_text():
    """Order is decided by matched characters, not matched units: three short lines can't outvote a long paragraph.
    (An unweighted chain would keep the three short lines in order and call the long paragraph 'moved'.)"""
    big = " ".join(P)
    old = ["None.", "Not applicable.", "See Note 9.", big]
    new = [big, "None.", "Not applicable.", "See Note 9."]
    ops, _, _ = run(old, new)
    assert ("unchanged", [3], [0]) in statuses(ops)
    assert sum(op.status == "moved" for op in ops) == 3


def test_reworded_and_moved_far_is_found_by_the_global_pass():
    """No neighbouring anchors tie these together, so only the global similarity pass (>= 0.5) can match them."""
    edited = P[1].replace("difficult to predict", "difficult to predict and to quantify with confidence")
    old = P[:6]
    new = [P[0], P[2], P[3], P[4], P[5], edited]
    ops, _, _ = run(old, new)
    (op,) = [o for o in ops if o.old == [1]]
    assert op.status == "moved" and op.new == [5] and op.facts["edited"] is True


def test_rewording_with_no_shared_three_word_phrase_is_found_by_the_gap_pass():
    """The global pass only nominates pairs sharing a word 3-gram. Here every 3-gram is broken, but the units sit
    between the same two neighbours and still score above the threshold, so the gap pass must match them."""
    words = "our ability to retain key personnel depends on compensation culture and labor market conditions".split()
    old_p = " ".join(words) + "."
    new_p = " ".join(w + " broadly" for w in words) + "."
    old, new = [P[0], old_p, P[2]], [P[0], new_p, P[2]]
    ops, _, _ = run(old, new)
    (op,) = [o for o in ops if o.old == [1]]
    assert op.status == "reworded" and op.facts.get("gap_match") is True


def test_split_and_merge():
    a = P[0] + " " + P[1]
    ops, _, _ = run([a, P[2]], [P[0], P[1], P[2]])
    kinds = {op.status for op in ops}
    assert "split" in kinds or "reworded" in kinds          # one half matches as reworded, the other as split
    assert not any(op.status == "added" for op in ops)
    ops, _, _ = run([P[0], P[1], P[2]], [a, P[2]])
    assert not any(op.status == "removed" for op in ops)


def test_repeated_identical_units_pair_in_order():
    old = [P[0], "None.", P[1], "None."]
    new = [P[0], "None.", P[1], "None."]
    ops, _, _ = run(old, new)
    assert {op.status for op in ops} == {"unchanged"}


def test_reworded_facts_are_deterministic_observations():
    old = [P[0].replace("in ways", "in 2024 in ways")]
    new = [P[0].replace("in ways", "in 2025 in ways")]
    (op,), _, _ = run(old, new)
    assert op.status == "reworded"
    assert op.facts["numbers_only"] is True and op.facts["formatting_only"] is False
    assert op.facts["changes"] == [{"op": "replace", "old": "2024", "new": "2025"}]


def test_formatting_only_fact():
    (op,), _, _ = run([P[0]], [P[0].upper()])
    assert op.status == "reworded" and op.facts["formatting_only"] is True


# --- determinism ------------------------------------------------------------------------------------------------------

def test_same_input_same_ops():
    old = P[:6] + ["None."]
    new = [P[5], P[0], P[1].replace("significant", "material"), "None.", P[3] + " " + P[4]]
    a, _, _ = run(old, new)
    b, _, _ = run(old, new)
    assert [(o.status, o.old, o.new, o.similarity, o.facts) for o in a] == \
           [(o.status, o.old, o.new, o.similarity, o.facts) for o in b]
