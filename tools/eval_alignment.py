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


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def as_run(items: list[dict]) -> None:
    """Set item['as_run'] from the current diffs: did the aligner pair the units holding these exact texts?

    Items are mapped to current units by their frozen text (a unit containing it), because segmentation fixes can
    renumber units. Also records whether an unmatched old unit was paired with some *other* unit instead.
    """
    cache: dict[str, dict] = {}
    for it in items:
        rec = cache.setdefault(it["file"], json.loads((ROOT / "data" / "diffs" / it["file"]).read_text(encoding="utf-8")))
        texts = {}
        for side in ("old", "new"):
            full = (ROOT / "data" / "sections" / rec[side]["accession"] / f"{rec['section']}.txt").read_text(
                encoding="utf-8")
            want = _norm(it[f"{side}_text"])
            hits = [k for k, (_, s, e) in enumerate(rec[f"{side}_units"]) if want in _norm(full[s:e])]
            texts[side] = hits[0] if hits else None
        o, n = texts["old"], texts["new"]
        pair = next((op for op in rec["ops"] if o in op["old"] and n in op["new"]), None)
        other = next((op for op in rec["ops"] if o in op["old"] and op["new"]), None)
        it["as_run"] = (pair["status"] if pair else ("elsewhere:" + other["status"] if other else "unmatched")) \
            if o is not None and n is not None else "unmapped"


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
    as_run(items)
    rules = {"aligner when labeled (ratio ≥ 0.5, gap ≥ 0.35)": lambda i: i["current"].startswith("matched ("),
             "**aligner as it runs now**": lambda i: i["as_run"] in ("unchanged", "reworded", "moved", "split",
                                                                     "merged")}
    for r in (0.35, 0.4, 0.45, 0.5, 0.55, 0.6):
        rules[f"ratio >= {r}"] = lambda i, r=r: i["ratio"] >= r
        for c in (0.6, 0.7, 0.8, 0.9):
            rules[f"ratio >= {r} or containment >= {c}"] = lambda i, r=r, c=c: i["ratio"] >= r or i["containment"] >= c
    lines += ["", "## Rules", "", "| Rule | Precision | Recall | F1 | raw tp/fp/fn/tn |", "|---|---|---|---|---|"]
    for name, f in rules.items():
        p, rc, f1, raw = score(items, pop, f)
        lines.append(f"| {name} | {p:.2f} | {rc:.2f} | {f1:.2f} | {raw.get('tp', 0)}/{raw.get('fp', 0)}/"
                     f"{raw.get('fn', 0)}/{raw.get('tn', 0)} |")
    lines += ["", "## Disagreements with the aligner as it runs now", "",
              "`elsewhere:` means the aligner paired the old paragraph with a *different* new paragraph. That can be a"
              " second valid counterpart, so those are listed separately from outright misses.", ""]
    for i in items:
        cur = rules["**aligner as it runs now**"](i)
        if cur != (i["label"] == "Y"):
            lines.append(f"- {i['id']} · {i['company']} · {i['section']} · label {i['label']} · aligner: {i['as_run']}"
                         f" · ratio {i['ratio']} · containment {i['containment']}")
    unmapped = [i["id"] for i in items if i["as_run"] == "unmapped"]
    lines += ["", f"Items that could not be mapped to current units: {unmapped or 'none'}."]
    (ROOT / "docs" / "alignment-eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(items)} labeled ({unsure} '?', {len(missing)} missing) -> docs/alignment-eval.md")


if __name__ == "__main__":
    main()
