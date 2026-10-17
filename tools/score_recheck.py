"""Score the adjudication re-check: the blind-test disagreements, relabeled with the context the classifier saw.

    python tools/score_recheck.py --import <dir>   # once: labels from the re-check page's db -> tests/golden/
    python tools/score_recheck.py                  # offline; writes docs/materiality-eval-test-adjudicated.md

The blind numbers (docs/materiality-eval-test.md) are the headline and are never replaced. This is a secondary number:
the re-check only revisits items where the labeler and the classifier disagreed, so it can only move agreement up, and
the labeler had seen the classifier's label being questioned. Both biases are stated in the output.
"""
from __future__ import annotations

import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_materiality import human_labels, to_item, weighted_pr  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / "materiality_recheck.json"
CONV = {"M": "material", "C": "cosmetic", "U": "unsure"}


def import_labels(src: Path) -> None:
    if GOLDEN.exists():
        raise SystemExit(f"{GOLDEN.name} already exists; refusing to overwrite a committed record.")
    labels = {}
    for f in sorted(src.rglob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        body = doc.get("data", doc)
        if re.fullmatch(r"M\d{3}", f.stem) and body.get("label") in CONV:
            labels[f.stem] = {"label": body["label"], "code": body.get("code") or None,
                              "note": body.get("note") or None, "at": body.get("at")}
    GOLDEN.write_text(json.dumps(labels, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"imported {len(labels)} re-check labels -> {GOLDEN.relative_to(ROOT)}")


def score(rows: list[dict], pop: dict, seed: int) -> tuple:
    scored = [x for x in rows if x["human"] in ("material", "cosmetic") and x["model"] in ("material", "cosmetic",
                                                                                         "unsure")]
    agree = sum(x["human"] == x["model"] for x in scored)
    decided = [x for x in scored if x["model"] != "unsure"]
    p, rc = weighted_pr(decided, pop)
    rng, by_s, ps, rs = random.Random(seed), defaultdict(list), [], []
    for x in decided:
        by_s[x["stratum"]].append(x)
    for _ in range(2000):
        bp, br = weighted_pr([rng.choice(v) for v in by_s.values() for _ in v], pop)
        if bp == bp and br == br:
            ps.append(bp)
            rs.append(br)
    ps.sort()
    rs.sort()
    ci = lambda xs: (xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1])  # noqa: E731
    return agree, len(scored), p, ci(ps), rc, ci(rs)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--import" in sys.argv:
        import_labels(Path(sys.argv[sys.argv.index("--import") + 1]))
        return
    recheck = json.loads(GOLDEN.read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "tests" / "golden" / "materiality_sample.json").read_text(encoding="utf-8"))
    items = {m["id"]: m for m in sample["items"] if m["split"] == "test"}
    blind = human_labels("test")
    res = {json.loads(line)["id"]: json.loads(line) for line in
           (ROOT / "data" / "classify" / "test-claude-sonnet-5-5.jsonl").read_text(encoding="utf-8").splitlines()}
    model = lambda i: res[i]["label"] if res[i]["outcome"] == "ok" else f"({res[i]['outcome']})"  # noqa: E731
    rows_b = [{"id": i, "stratum": items[i]["stratum"], "human": blind.get(i), "model": model(i)} for i in items]
    rows_a = [{**x, "human": CONV[recheck[x["id"]]["label"]] if x["id"] in recheck else x["human"]} for x in rows_b]
    pop = sample["population"]
    b, a = score(rows_b, pop, 20261015), score(rows_a, pop, 20261015)

    moved = Counter()
    lines_items = []
    for i in sorted(recheck):
        old, new, m = blind[i], CONV[recheck[i]["label"]], model(i)
        ctx = to_item(items[i])["context"]
        restated = bool(ctx and ctx.get("kind") == "restated")
        kind = "to classifier" if new == m else ("unsure" if new == "unsure" else "held")
        moved[(kind, restated)] += 1
        lines_items.append(f"| {i} | {items[i]['stratum']} | {'yes' if restated else 'no'} | {old} | {m} | **{new}** "
                           f"| {kind} |")
    times = sorted(datetime.fromisoformat(v["at"].replace("Z", "+00:00")) for v in recheck.values() if v.get("at"))
    gaps = [(t2 - t1).total_seconds() for t1, t2 in zip(times, times[1:]) if (t2 - t1).total_seconds() < 600]
    tot = lambda k: moved[(k, True)] + moved[(k, False)]  # noqa: E731
    fmt = lambda s: (f"{s[0]}/{s[1]} ({s[0] / s[1]:.0%}) · precision **{s[2]:.2f}** ({s[3][0]:.2f}–{s[3][1]:.2f}) · "  # noqa: E731
                     f"recall **{s[4]:.2f}** ({s[5][0]:.2f}–{s[5][1]:.2f})")
    lines = ["# Materiality evaluation: test set, adjudicated (secondary)", "",
             "**The headline is the blind result** (`docs/materiality-eval-test.md`). This page re-scores the same "
             f"classifier output (`claude-sonnet-5-5`, prompt `1fd1c7e5bb42`) after Trevor relabeled the {len(recheck)} "
             "disagreements with the context the classifier saw (the restatement passages), without the classifier's "
             "label or rationale. Labels: `tests/golden/materiality_recheck.json`. Generated by "
             "`tools/score_recheck.py` (offline).", "",
             "| | agreement · \"material\" precision (95% CI) · recall (95% CI) |", "|---|---|",
             f"| blind (headline) | {fmt(b)} |", f"| adjudicated | {fmt(a)} |", "",
             "Stratum-weighted, stratified bootstrap with 2,000 resamples, same seed as the blind run. Items "
             "relabeled **U** leave the scored set, as unsure human labels do in the blind run.", "",
             "## What the re-check changed", "",
             f"- Relabeled to the classifier's label: **{tot('to classifier')}** ({moved[('to classifier', True)]} "
             f"of them had restatement context). Held the blind label: **{tot('held')}** "
             f"({moved[('held', True)]} with context). Now unsure: **{tot('unsure')}**.",
             f"- **The information-gap explanation mostly fails.** The blind error analysis attributed the misses to "
             f"the labeling sheet not showing restatement context. Shown that context, Trevor kept his label on "
             f"{moved[('held', True)]} of the {sum(v for (k, r), v in moved.items() if r)} items that had it, every "
             "split/merged one included. Those are a real disagreement about the guide: the classifier treats "
             "restated text as cosmetic (tie-break rule 3 plus the classifier notes), while Trevor treats a "
             "restructured passage that adds or drops disclosure as material.",
             f"- Re-check pace: median {statistics.median(gaps):.0f} s between labels (blind pass: 16 s).",
             "", "## Why this is not the accuracy figure", "",
             "- Only disagreements were revisited. Agreements were never re-checked, so errors where both sides were "
             "wrong the same way stay hidden, and agreement can only rise.",
             "- The labeler knew every item on the page was a disagreement. That invites deference to the classifier "
             "even though its label was not shown.",
             "- What it does measure is how much of the blind gap came from the labeler and the classifier seeing "
             "different context, the information gap found in the error analysis.", "",
             "## Items", "", "| id | stratum | restatement context | blind | classifier | re-check | outcome |",
             "|---|---|---|---|---|---|---|", *lines_items, ""]
    (ROOT / "docs" / "materiality-eval-test-adjudicated.md").write_text("\n".join(lines), encoding="utf-8",
                                                                       newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
