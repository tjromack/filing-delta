"""Build the alignment labeling sheet: real candidate paragraph pairs for a human to label (M3, FD-DEC 018).

    python tools/alignment_sample.py          # writes docs/alignment-labeling.md (labels are filled in there)

For every old paragraph (at least 15 tokens) in every full diff pair, the best new paragraph candidate is found by
token-sequence similarity ("ratio") and by containment (matched tokens / the shorter paragraph's tokens). Candidates
are stratified by ratio band x containment bin and sampled deterministically (sha256 order, at most 2 per filing
pair per stratum), so the sheet covers the pairs the aligner accepts as well as the ones it rejects. The labels, not
anyone's eyeballing, then set the thresholds and give the aligner's published precision and recall.
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.diff.normalize import tokens  # noqa: E402

SEC = ROOT / "data" / "sections"
RATIO_BANDS = [(0.25, 0.35), (0.35, 0.5), (0.5, 0.6), (0.6, 0.75)]
PER_STRATUM = 10
MIN_TOKENS = 15


def shingles(t):
    return {tuple(t[i:i + 3]) for i in range(len(t) - 2)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pool = []
    for f in sorted(glob.glob(str(ROOT / "data" / "diffs" / "*.json"))):
        rec = json.loads(Path(f).read_text(encoding="utf-8"))
        if rec["state"] != "full -> full":
            continue
        to = (SEC / rec["old"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        tn = (SEC / rec["new"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        match_of = {}
        for op in rec["ops"]:
            if len(op["old"]) == 1 and len(op["new"]) == 1:
                match_of[op["old"][0]] = (op["new"][0], op["status"])
        news = {j: tokens(tn[u[1]:u[2]]) for j, u in enumerate(rec["new_units"]) if u[0] == "paragraph"}
        index = defaultdict(list)
        for j, t in news.items():
            if len(t) >= MIN_TOKENS:
                for s in shingles(t):
                    index[s].append(j)
        for i, u in enumerate(rec["old_units"]):
            if u[0] != "paragraph":
                continue
            a = tokens(to[u[1]:u[2]])
            if len(a) < MIN_TOKENS:
                continue
            cand = set()
            for s in shingles(a):
                hits = index.get(s, ())
                if len(hits) <= 50:
                    cand.update(hits)
            if not cand:
                continue
            best = None
            for j in sorted(cand):
                b = news[j]
                sm = SequenceMatcher(None, a, b, autojunk=False)
                m = sum(x.size for x in sm.get_matching_blocks())
                ratio = 2 * m / (len(a) + len(b))
                cont = m / min(len(a), len(b))
                score = max(ratio, cont)
                if best is None or score > best[0]:
                    best = (score, j, ratio, cont)
            _, j, ratio, cont = best
            if ratio >= 0.75 or ratio < 0.25:
                continue
            cur = match_of.get(i)
            decision = ("matched (" + cur[1] + ")") if cur and cur[0] == j else (
                "matched elsewhere" if cur else "not matched (removed)")
            pool.append({
                "file": Path(f).name, "company": rec["company"], "section": rec["section"],
                "old_date": rec["old"]["report_date"], "new_date": rec["new"]["report_date"],
                "old_unit": i, "new_unit": j, "ratio": round(ratio, 3), "containment": round(cont, 3),
                "current": decision,
                "old_text": to[u[1]:u[2]], "new_text": tn[rec["new_units"][j][1]:rec["new_units"][j][2]],
            })
    strata = defaultdict(list)
    for p in pool:
        band = next(b for b in RATIO_BANDS if b[0] <= p["ratio"] < b[1])
        strata[(band, p["containment"] >= 0.6)].append(p)
    chosen = []
    for key in sorted(strata):
        items = sorted(strata[key], key=lambda p: hashlib.sha256(
            f"{p['file']}:{p['old_unit']}:{p['new_unit']}".encode()).hexdigest())
        per_file = defaultdict(int)
        picked = []
        for p in items:
            if per_file[p["file"]] >= 2:
                continue
            per_file[p["file"]] += 1
            picked.append(p)
            if len(picked) == PER_STRATUM:
                break
        chosen += picked
    chosen.sort(key=lambda p: hashlib.sha256(f"{p['file']}:{p['old_unit']}".encode()).hexdigest())  # blind order
    out = [
        "# Alignment labeling sheet",
        "",
        "For each pair, decide one question: **is the NEW paragraph the same disclosure as the OLD one?**",
        "",
        "- **Y**: yes. The same disclosure, reworded, updated (new numbers or dates), expanded, or shortened. A reader"
        " would call it a revision of the old paragraph, not a new topic.",
        "- **N**: no. A different disclosure, even if it shares boilerplate phrasing (\"could adversely affect our"
        " business…\").",
        "- **?**: you can't tell from these two texts.",
        "",
        "Write the letter after **Label:**. Scores and the aligner's current decision are deliberately not shown, so"
        " they can't influence the label. They're in `tests/golden/alignment_sample.json`, keyed by item id.",
        "Texts longer than 1,500 characters are cut, and the cut is marked.",
        "",
    ]
    meta = []
    for n, p in enumerate(chosen, 1):
        cut = lambda s: s if len(s) <= 1500 else s[:1500] + " […cut]"  # noqa: E731
        out += [f"## A{n:02d} · {p['company']} · {p['section']} · {p['old_date']} → {p['new_date']}", "",
                "**OLD:**", "", "> " + cut(p["old_text"]).replace("\n\n", "\n>\n> "), "",
                "**NEW:**", "", "> " + cut(p["new_text"]).replace("\n\n", "\n>\n> "), "",
                "**Label:** ", "", "**Note (optional):** ", ""]
        meta.append({"id": f"A{n:02d}", **{k: p[k] for k in ("file", "company", "section", "old_date", "new_date",
                                                              "old_unit", "new_unit", "ratio", "containment",
                                                              "current")}})
    (ROOT / "docs" / "alignment-labeling.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    for m in meta:
        band = next(b for b in RATIO_BANDS if b[0] <= m["ratio"] < b[1])
        m["stratum"] = f"ratio {band[0]}-{band[1]} · containment {'>=' if m['containment'] >= 0.6 else '<'}0.6"
    population = {f"ratio {b[0]}-{b[1]} · containment {'>=' if hi else '<'}0.6": len(v) for (b, hi), v in strata.items()}
    (ROOT / "tests" / "golden" / "alignment_sample.json").write_text(
        json.dumps({"population": dict(sorted(population.items())), "items": meta}, indent=1, ensure_ascii=False)
        + "\n", encoding="utf-8", newline="\n")
    counts = defaultdict(int)
    for p in chosen:
        counts[(next(b for b in RATIO_BANDS if b[0] <= p["ratio"] < b[1]), p["containment"] >= 0.6)] += 1
    print(f"pool {len(pool)} candidate pairs; sampled {len(chosen)}:", dict(counts))


if __name__ == "__main__":
    main()
