"""Sweep the aligner's threshold and score the *whole aligner* (with its 1:1 competition) against the labels.

    python tools/sweep_alignment.py

For each candidate REWORD_MIN, re-diffs only the filing pairs the labeled sample comes from (in memory; data/diffs
is not touched) and scores precision/recall exactly as tools/eval_alignment.py does for "aligner as it runs now".
Pairwise rules can't see that a paragraph's best partner is taken by a better match, so the whole aligner is what
gets tuned (FD-DEC 018).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import eval_alignment as ev  # noqa: E402
from filing_delta.diff import align as al  # noqa: E402
from filing_delta.diff.run import _load, _text, diff_pair  # noqa: E402

THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sample = json.loads((ROOT / "tests" / "golden" / "alignment_sample.json").read_text(encoding="utf-8"))
    pop, meta = sample["population"], sample["items"]
    lab = ev.labels()
    items = [{**m, "label": lab[m["id"]]} for m in meta if lab.get(m["id"]) in ("Y", "N")]
    sec = ROOT / "data" / "sections"
    rows = {(r["accession"], r["section"]): r for r in _load(sec)}
    files = sorted({i["file"] for i in items})
    pairs = {}
    for f in files:
        rec = json.loads((ROOT / "data" / "diffs" / f).read_text(encoding="utf-8"))
        a = rows[(rec["old"]["accession"], rec["section"])]
        b = rows[(rec["new"]["accession"], rec["section"])]
        pairs[f] = (a, b, _text(sec, a), _text(sec, b))
    out = ["| REWORD_MIN | Precision | Recall | F1 | raw tp/fp/fn/tn |", "|---|---|---|---|---|"]
    for t in THRESHOLDS:
        al.REWORD_MIN = al.GAP_MIN = t
        recs = {f: diff_pair(*pairs[f]) for f in files}
        for it in items:
            rec = recs[it["file"]]
            ids = {}
            for side in ("old", "new"):
                full = pairs[it["file"]][2 if side == "old" else 3]
                want = ev._norm(it[f"{side}_text"])
                hits = [k for k, (_, s, e) in enumerate(rec[f"{side}_units"]) if want in ev._norm(full[s:e])]
                ids[side] = hits[0] if hits else None
            pair = next((op for op in rec["ops"] if ids["old"] in op["old"] and ids["new"] in op["new"]), None)
            it["as_run"] = pair["status"] if pair else "unmatched"
        p, r, f1, raw = ev.score(items, pop, lambda i: i["as_run"] in ("unchanged", "reworded", "moved", "split",
                                                                      "merged"))
        out.append(f"| {t:.2f} | {p:.2f} | {r:.2f} | {f1:.2f} | {raw.get('tp', 0)}/{raw.get('fp', 0)}/"
                   f"{raw.get('fn', 0)}/{raw.get('tn', 0)} |")
        print(out[-1], flush=True)
    path = ROOT / "docs" / "alignment-eval.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\n## Whole-aligner threshold sweep\n.*?(?=\n## |\Z)", "", text, flags=re.S)
    text = text.rstrip("\n") + "\n\n## Whole-aligner threshold sweep\n\nThe aligner re-run at each threshold on the " \
        f"{len(files)} filing pairs the sample comes from, scored as it runs (1:1 competition included):\n\n" + \
        "\n".join(out) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
