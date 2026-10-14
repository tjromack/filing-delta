"""Align two versions of a section unit by unit, deterministically (M3). No model calls.

Statuses: unchanged · reworded · moved (in-order or not, edited or not) · split · merged · added · removed.

1. Exact matches: units with equal keys. Occurrences of a repeated key are paired in order.
2. Fuzzy matches among the remaining units of the same kind: candidates share a word 3-gram; similarity is the
   token-sequence ratio (difflib); pairs at or above `REWORD_MIN` are accepted greedily, best first.
3. Splits and merges: a still-unmatched unit whose 3-grams are mostly (`COVER_MIN`) contained in one unit on the
   other side.
4. Order: a maximum-weight increasing subsequence over the 1:1 matches (weight = matched characters) keeps the
   in-order ones. The rest are *moved*. A big paragraph is never displaced by a small one.

Every tie is broken by position, so the same input always gives the same output.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .normalize import tokens
from .segment import Unit

# Set from 70 human labels under the *instance* criterion (FD-DEC 018; docs/alignment-eval.md). Scored on the
# whole aligner as it runs, 0.35-0.45 is a plateau (F1 ~0.82) and 0.50 drops recall to 0.66. 0.40 is the middle of
# the plateau.
REWORD_MIN = 0.40      # token-sequence similarity for "the same paragraph, reworded"
GAP_MIN = REWORD_MIN   # the gap pass nominates candidates by position; it doesn't lower the bar
GAP_MAX_PAIRS = 40_000 # a gap bigger than this (old x new units) is left to the global pass
COVER_MIN = 0.8        # share of a unit's 3-grams found in one unit on the other side, for split/merge
MIN_SHINGLES = 5       # a split/merge needs at least this many 3-grams (fragments like "None." can't qualify)
COMMON_SHINGLE = 50    # 3-grams in more units than this are boilerplate; they don't nominate candidates


@dataclass
class Op:
    status: str
    old: list[int] = field(default_factory=list)
    new: list[int] = field(default_factory=list)
    similarity: float = 1.0
    facts: dict = field(default_factory=dict)


def _shingles(toks: list[str]) -> set[tuple]:
    if len(toks) < 3:
        return {tuple(toks)} if toks else set()
    return {tuple(toks[i:i + 3]) for i in range(len(toks) - 2)}


def _max_weight_increasing(pairs: list[tuple[int, int, float]]) -> set[int]:
    """Indices of `pairs` (old, new, weight), sorted by old, forming the max-weight chain increasing in new."""
    order = sorted(range(len(pairs)), key=lambda i: (pairs[i][0], pairs[i][1]))
    news = sorted({p[1] for p in pairs})
    rank = {v: r + 1 for r, v in enumerate(news)}
    size = len(news)
    tree_w = [0.0] * (size + 1)
    tree_i = [-1] * (size + 1)
    best_w: dict[int, float] = {}
    prev: dict[int, int] = {}

    def query(r: int) -> tuple[float, int]:
        w, at = 0.0, -1
        while r > 0:
            if tree_w[r] > w or (tree_w[r] == w and at != -1 and tree_i[r] != -1 and tree_i[r] < at):
                w, at = tree_w[r], tree_i[r]
            r -= r & -r
        return w, at

    def update(r: int, w: float, i: int) -> None:
        while r <= size:
            if w > tree_w[r] or (w == tree_w[r] and (tree_i[r] == -1 or i < tree_i[r])):
                tree_w[r], tree_i[r] = w, i
            r += r & -r

    for i in order:
        o, n, w = pairs[i]
        pw, pi = query(rank[n] - 1)
        best_w[i] = pw + w
        prev[i] = pi
        update(rank[n], best_w[i], i)
    if not best_w:
        return set()
    end = max(best_w, key=lambda i: (best_w[i], -pairs[i][0]))
    chain = set()
    while end != -1:
        chain.add(end)
        end = prev[end]
    return chain


def _facts(a_text: str, b_text: str, a: Unit, b: Unit) -> dict:
    """Deterministic word-level facts about a reworded pair (inputs for the M4 classifier, not judgments)."""
    ta, tb = tokens(a_text), tokens(b_text)
    changes = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, ta, tb, autojunk=False).get_opcodes():
        if tag != "equal":
            changes.append({"op": tag, "old": " ".join(ta[i1:i2]), "new": " ".join(tb[j1:j2])})
    changed = [w for c in changes for w in (c["old"] + " " + c["new"]).split()]
    return {
        "formatting_only": a.loose == b.loose,
        "numbers_only": bool(changed) and all(any(ch.isdigit() for ch in w) or w in ("$", "%") for w in changed),
        "words_changed": sum(len(c["old"].split()) + len(c["new"].split()) for c in changes),
        "changes": changes[:200],
    }


def align(old_text: str, old: list[Unit], new_text: str, new: list[Unit]) -> list[Op]:
    old_used: set[int] = set()
    new_used: set[int] = set()
    matches: list[tuple[int, int, float]] = []          # (old idx, new idx, similarity)

    # 1. Exact matches by key, occurrences paired in order.
    by_key_new: dict[str, list[int]] = defaultdict(list)
    for u in new:
        by_key_new[u.key].append(u.idx)
    taken: dict[str, int] = defaultdict(int)
    for u in old:
        lst = by_key_new.get(u.key)
        if lst and taken[u.key] < len(lst):
            n = lst[taken[u.key]]
            taken[u.key] += 1
            matches.append((u.idx, n, 1.0))
            old_used.add(u.idx)
            new_used.add(n)

    # 2. Fuzzy matches among the rest, same kind only.
    otoks = {u.idx: tokens(old_text[u.start:u.end]) for u in old if u.idx not in old_used}
    ntoks = {u.idx: tokens(new_text[u.start:u.end]) for u in new if u.idx not in new_used}
    osh = {i: _shingles(t) for i, t in otoks.items()}
    nsh = {i: _shingles(t) for i, t in ntoks.items()}
    index: dict[tuple, list[int]] = defaultdict(list)
    for i in sorted(nsh):
        for s in nsh[i]:
            index[s].append(i)
    cands: list[tuple[float, int, int]] = []
    for i in sorted(osh):
        seen: set[int] = set()
        for s in osh[i]:
            hits = index.get(s, ())
            if len(hits) <= COMMON_SHINGLE:
                seen.update(hits)
        for j in sorted(seen):
            if old[i].kind != new[j].kind:
                continue
            a, b = otoks[i], ntoks[j]
            # Cheap upper bound before the quadratic ratio.
            if 2 * min(len(a), len(b)) / (len(a) + len(b)) < REWORD_MIN:
                continue
            r = SequenceMatcher(None, a, b, autojunk=False).ratio()
            if r >= REWORD_MIN:
                cands.append((r, i, j))
    for r, i, j in sorted(cands, key=lambda c: (-c[0], c[1], c[2])):
        if i in old_used or j in new_used:
            continue
        matches.append((i, j, r))
        old_used.add(i)
        new_used.add(j)

    # 2b. Gap pass: the global pass only *nominates* pairs that share a word 3-gram, so a heavy rewording with no
    # three words in common is never considered. Here, units left in the same gap between consecutive in-order
    # matches are nominated by position instead. The acceptance bar is the same labeled threshold.
    chain1 = _max_weight_increasing([(o, n, (new[n].end - new[n].start) * s) for o, n, s in matches])
    anchors = sorted((matches[k][0], matches[k][1]) for k in chain1)
    bounds = [(-1, -1)] + anchors + [(len(old), len(new))]
    gap_cands: list[tuple[float, int, int]] = []
    for (o0, n0), (o1, n1) in zip(bounds, bounds[1:]):
        gold = [i for i in range(o0 + 1, o1) if i not in old_used]
        gnew = [j for j in range(n0 + 1, n1) if j not in new_used]
        if not gold or not gnew or len(gold) * len(gnew) > GAP_MAX_PAIRS:
            continue
        for i in gold:
            a = otoks.get(i) or tokens(old_text[old[i].start:old[i].end])
            for j in gnew:
                if old[i].kind != new[j].kind or old[i].kind == "heading":
                    continue
                b = ntoks.get(j) or tokens(new_text[new[j].start:new[j].end])
                if not a or not b or 2 * min(len(a), len(b)) / (len(a) + len(b)) < GAP_MIN:
                    continue
                r = SequenceMatcher(None, a, b, autojunk=False).ratio()
                if r >= GAP_MIN:
                    gap_cands.append((r, i, j))
    gap_matched: set[tuple[int, int]] = set()
    for r, i, j in sorted(gap_cands, key=lambda c: (-c[0], c[1], c[2])):
        if i in old_used or j in new_used:
            continue
        matches.append((i, j, r))
        gap_matched.add((i, j))
        old_used.add(i)
        new_used.add(j)

    # 3. Order: the max-weight in-order chain; the rest moved.
    weights = [(o, n, (new[n].end - new[n].start) * s) for o, n, s in matches]
    chain = _max_weight_increasing(weights)
    ops: list[Op] = []
    for k, (o, n, s) in enumerate(matches):
        in_order = k in chain
        exact = old[o].key == new[n].key
        if exact:
            ops.append(Op("unchanged" if in_order else "moved", [o], [n], 1.0, {"edited": False}))
        else:
            facts = _facts(old_text[old[o].start:old[o].end], new_text[new[n].start:new[n].end], old[o], new[n])
            if not in_order:
                facts["edited"] = True
            if (o, n) in gap_matched:
                facts["gap_match"] = True
            ops.append(Op("reworded" if in_order else "moved", [o], [n], round(s, 4), facts))

    # 4. Splits and merges among what is still unmatched.
    all_osh = {u.idx: osh.get(u.idx) or _shingles(tokens(old_text[u.start:u.end])) for u in old}
    all_nsh = {u.idx: nsh.get(u.idx) or _shingles(tokens(new_text[u.start:u.end])) for u in new}
    split_into: dict[int, list[int]] = defaultdict(list)
    for j in sorted(set(range(len(new))) - new_used):
        sj = all_nsh[j]
        if len(sj) < MIN_SHINGLES:
            continue
        best = max(((len(sj & all_osh[i]) / len(sj), -i) for i in range(len(old)) if old[i].kind == new[j].kind),
                   default=(0.0, 0))
        if best[0] >= COVER_MIN:
            split_into[-best[1]].append(j)
            new_used.add(j)
    for i, js in sorted(split_into.items()):
        ops.append(Op("split", [i], sorted(js), 1.0, {"coverage_min": COVER_MIN}))
    merged_into: dict[int, list[int]] = defaultdict(list)
    for i in sorted(set(range(len(old))) - old_used):
        si = all_osh[i]
        if len(si) < MIN_SHINGLES:
            continue
        best = max(((len(si & all_nsh[j]) / len(si), -j) for j in range(len(new)) if new[j].kind == old[i].kind),
                   default=(0.0, 0))
        if best[0] >= COVER_MIN:
            merged_into[-best[1]].append(i)
            old_used.add(i)
    for j, is_ in sorted(merged_into.items()):
        ops.append(Op("merged", sorted(is_), [j], 1.0, {"coverage_min": COVER_MIN}))

    ops += [Op("removed", [i], [], 0.0) for i in range(len(old)) if i not in old_used]
    ops += [Op("added", [], [j], 0.0) for j in range(len(new)) if j not in new_used]
    # Reading order: by position in the new version; removed units sit where they were in the old version.
    new_pos_of_old = {o: n for op in ops for o in op.old for n in op.new[:1]}

    def sort_key(op: Op) -> tuple:
        if op.new:
            return (min(op.new), 0, min(op.old) if op.old else -1)
        o = op.old[0]
        before = [new_pos_of_old[x] for x in range(o, -1, -1) if x in new_pos_of_old]
        return (before[0] if before else -1, 1, o)

    return sorted(ops, key=sort_key)
