"""Score candidate alignment rules against the human labels; write docs/alignment-eval.md (M3, FD-DEC 018).

    python tools/eval_alignment.py

Reads the labels written in docs/alignment-labeling.md (Y / N / ?) and the hidden scores in
tests/golden/alignment_sample.json. The sample is stratified, so every estimate is weighted by its stratum's
share of the full candidate population (unweighted numbers are shown too). '?' labels are excluded and counted.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def labels() -> dict[str, str]:
    text = (ROOT / "docs" / "alignment-labeling.md").read_text(encoding="utf-8")
    out = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        ident = block.split(" ", 1)[0]
        m = re.search(r"\*\*Label:\*\*[ \t]*([YNyn?])", block)
        if m:
            out[ident] = m.group(1).upper()
    return out


def score(items, pop, predict):
    """Weighted precision/recall: each labeled item stands for (stratum population / labeled in stratum) pairs."""
    per = defaultdict(int)
    for it in items:
        per[it["stratum"]] += 1
    tp = fp = fn = tn = 0.0
    raw = defaultdict(int)
    for it in items:
        w = pop[it["stratum"]] / per[it["stratum"]]
        p, y = predict(it), it["label"] == "Y"
        key = ("tp" if y else "fp") if p else ("fn" if y else "tn")
        raw[key] += 1
        if key == "tp":
            tp += w
        elif key == "fp":
            fp += w
        elif key == "fn":
            fn += w
        else:
            tn += w
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else float("nan")
    return prec, rec, f1, dict(raw)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sample = json.loads((ROOT / "tests" / "golden" / "alignment_sample.json").read_text(encoding="utf-8"))
    pop, meta = sample["population"], sample["items"]
    lab = labels()
    items = [{**m, "label": lab[m["id"]]} for m in meta if m["id"] in lab and lab[m["id"]] in "YN"]
    unsure = sum(1 for m in meta if lab.get(m["id"]) == "?")
    missing = [m["id"] for m in meta if m["id"] not in lab]
    lines = ["# Alignment evaluation", "",
             f"Human labels: {len(items)} Y/N, {unsure} '?', {len(missing)} unlabeled, out of {len(meta)} sampled pairs.",
             "Estimates are weighted by each stratum's share of the {:,} candidate pairs (raw counts in brackets).".format(
                 sum(pop.values())), "",
             "## Labels by stratum", "", "| Stratum | Population | Labeled | Y | N |", "|---|---|---|---|---|"]
    for s in sorted(pop):
        its = [i for i in items if i["stratum"] == s]
        lines.append(f"| {s} | {pop[s]:,} | {len(its)} | {sum(i['label'] == 'Y' for i in its)} | "
                     f"{sum(i['label'] == 'N' for i in its)} |")
    rules = {"current aligner (as run)": lambda i: i["current"].startswith("matched (")}
    for r in (0.35, 0.4, 0.45, 0.5, 0.55, 0.6):
        rules[f"ratio >= {r}"] = lambda i, r=r: i["ratio"] >= r
        for c in (0.6, 0.7, 0.8, 0.9):
            rules[f"ratio >= {r} or containment >= {c}"] = lambda i, r=r, c=c: i["ratio"] >= r or i["containment"] >= c
    lines += ["", "## Rules", "", "| Rule | Precision | Recall | F1 | raw tp/fp/fn/tn |", "|---|---|---|---|---|"]
    for name, f in rules.items():
        p, rc, f1, raw = score(items, pop, f)
        lines.append(f"| {name} | {p:.2f} | {rc:.2f} | {f1:.2f} | {raw.get('tp', 0)}/{raw.get('fp', 0)}/"
                     f"{raw.get('fn', 0)}/{raw.get('tn', 0)} |")
    lines += ["", "## Disagreements with the current aligner", ""]
    for i in items:
        cur = i["current"].startswith("matched (")
        if cur != (i["label"] == "Y"):
            lines.append(f"- {i['id']} · {i['company']} · {i['section']} · label {i['label']} · aligner: {i['current']}"
                         f" · ratio {i['ratio']} · containment {i['containment']}")
    (ROOT / "docs" / "alignment-eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(items)} labeled ({unsure} '?', {len(missing)} missing) -> docs/alignment-eval.md")


if __name__ == "__main__":
    main()
