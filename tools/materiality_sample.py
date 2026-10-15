"""Build the M4 labeling sheets: 150 stratified Item 1A changes, split 30 dev / 120 test (docs/design/materiality.md §3).

    python tools/materiality_sample.py

Writes docs/materiality-labels-dev.md, docs/materiality-labels-test.md (Trevor labels there), and
tests/golden/materiality_sample.json (stratum populations, item metadata, frozen texts). Deterministic: sha256 order
within each stratum, round-robin across companies. The dev/test assignment is fixed here, before any model runs.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.diff.display import inline_diff  # noqa: E402
SEC = ROOT / "data" / "sections"
QUOTA = {  # stratum -> items (150 total)
    "formatting_only": 12, "numbers_only": 10,
    "reworded 0.40-0.60": 15, "reworded 0.60-0.80": 15, "reworded 0.80-0.95": 15, "reworded 0.95-1.00": 15,
    "moved (edited)": 12, "split/merged": 12, "added": 22, "removed": 22,
}
DEV_SHARE = 0.2
LABEL = {"10K_1A": "10-K Item 1A", "10Q_P2_1A": "10-Q Part II Item 1A"}


def stratum(op: dict) -> str | None:
    st, facts = op["status"], op.get("facts", {})
    if st == "unchanged" or (st == "moved" and not facts.get("edited")):
        return None
    if facts.get("formatting_only"):
        return "formatting_only"
    if facts.get("numbers_only"):
        return "numbers_only"
    if st == "reworded":
        s = op["similarity"]
        for lo, hi in ((0.4, 0.6), (0.6, 0.8), (0.8, 0.95), (0.95, 1.01)):
            if lo <= s < hi:
                return f"reworded {lo:.2f}-{min(hi, 1.0):.2f}"
        return None
    if st == "moved":
        return "moved (edited)"
    if st in ("split", "merged"):
        return "split/merged"
    return st  # added / removed


def closest(text: str, candidates: list[str]) -> tuple[float, str]:
    words = text.split()
    best = (0.0, "")
    for c in candidates:
        r = SequenceMatcher(None, words, c.split(), autojunk=False).ratio()
        if r > best[0]:
            best = (r, c)
    return best


def main() -> None:
    # Never overwrite human work: refuse if either sheet already holds a label (this happened once, on M4).
    for split in ("dev", "test"):
        sheet = ROOT / "docs" / f"materiality-labels-{split}.md"
        if sheet.exists() and re.search(r"\*\*Label:\*\*[ \t]*[MCUmcu]", sheet.read_text(encoding="utf-8")) \
                and "--force" not in sys.argv:
            raise SystemExit(f"{sheet.name} already contains labels; refusing to overwrite (use --force).")
    pool: dict[str, list[dict]] = defaultdict(list)
    for f in sorted(glob.glob(str(ROOT / "data" / "diffs" / "*.json"))):
        rec = json.loads(Path(f).read_text(encoding="utf-8"))
        if rec["state"] != "full -> full" or rec["section"] not in LABEL:
            continue
        to = (SEC / rec["old"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        tn = (SEC / rec["new"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        ot = lambda i: to[rec["old_units"][i][1]:rec["old_units"][i][2]]  # noqa: E731
        nt = lambda j: tn[rec["new_units"][j][1]:rec["new_units"][j][2]]  # noqa: E731
        for k, op in enumerate(rec["ops"]):
            s = stratum(op)
            if s is None:
                continue
            pool[s].append({"file": Path(f).name, "op": k, "company": rec["company"], "section": rec["section"],
                            "old_date": rec["old"]["report_date"], "new_date": rec["new"]["report_date"],
                            "status": op["status"], "similarity": op["similarity"], "stratum": s,
                            "old_units": op["old"], "new_units": op["new"],
                            "old_text": "\n\n".join(ot(i) for i in op["old"]),
                            "new_text": "\n\n".join(nt(j) for j in op["new"]),
                            "_old_all": None, "_new_all": None, "_rec": (to, tn, rec)})
    chosen = []
    for s, quota in QUOTA.items():
        items = sorted(pool[s], key=lambda p: hashlib.sha256(f"{p['file']}:{p['op']}".encode()).hexdigest())
        by_co: dict[str, list[dict]] = defaultdict(list)
        for p in items:
            by_co[p["company"]].append(p)
        picked, cos = [], sorted(by_co)
        while len(picked) < min(quota, len(items)):
            for c in cos:
                if by_co[c] and len(picked) < quota:
                    picked.append(by_co[c].pop(0))
        n_dev = round(quota * DEV_SHARE)
        for n, p in enumerate(picked):
            p["split"] = "dev" if n < n_dev else "test"
        chosen += picked
    # Context for added/removed: the closest paragraph on the other side of the same pair.
    for p in chosen:
        to, tn, rec = p.pop("_rec")
        p.pop("_old_all"), p.pop("_new_all")
        if p["status"] == "added":
            r, c = closest(p["new_text"], [to[s:e] for k, s, e in rec["old_units"] if k == "paragraph"])
            p["context"] = {"side": "old", "similarity": round(r, 2), "text": c} if r >= 0.2 else None
        elif p["status"] == "removed":
            r, c = closest(p["old_text"], [tn[s:e] for k, s, e in rec["new_units"] if k == "paragraph"])
            p["context"] = {"side": "new", "similarity": round(r, 2), "text": c} if r >= 0.2 else None
        else:
            p["context"] = None
    # Blind order within each sheet, then ids.
    for n, p in enumerate(sorted(chosen, key=lambda p: hashlib.sha256(f"{p['file']}:{p['op']}:id".encode()).hexdigest()), 1):
        p["id"] = f"M{n:03d}"
    chosen.sort(key=lambda p: p["id"])
    population = {s: len(pool[s]) for s in QUOTA}
    meta = [{k: v for k, v in p.items()} for p in chosen]
    (ROOT / "tests" / "golden" / "materiality_sample.json").write_text(
        json.dumps({"population": population, "items": meta}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    # Never cut: a label must be given on the whole text (long unchanged runs inside diffs are collapsed instead).
    quote = lambda s: "> " + s.replace("\n\n", "\n>\n> ")  # noqa: E731
    for split in ("dev", "test"):
        items = [p for p in chosen if p["split"] == split]
        out = [f"# Materiality labels: {split} set ({len(items)} changes)", "",
               "Label each change against `docs/design/materiality.md` §2: **M** (material) · **C** (cosmetic) · "
               "**U** (unsure). Optionally add one code after it, e.g. `M severity` or `C rewording`. Write it after "
               "**Label:**. The model's output is not shown, and won't be until both sets are labeled.", "",
               "Inline changes: `[-deleted words-]` `{+inserted words+}`.", ""]
        for p in items:
            out += [f"## {p['id']} · {p['company']} · {LABEL[p['section']]} · {p['old_date']} → {p['new_date']} · "
                    f"**{p['status']}**", ""]
            if p["status"] in ("reworded", "moved"):
                out += ["**Change:**", "", quote(inline_diff(p["old_text"], p["new_text"])), ""]
            elif p["status"] == "added":
                out += ["**Added (NEW only):**", "", quote(p["new_text"]), ""]
                if p["context"]:
                    out += [f"*Closest OLD paragraph (similarity {p['context']['similarity']}), for context:*", "",
                            quote(p["context"]["text"]), ""]
                else:
                    out += ["*No similar OLD paragraph.*", ""]
            elif p["status"] == "removed":
                out += ["**Removed (OLD only):**", "", quote(p["old_text"]), ""]
                if p["context"]:
                    out += [f"*Closest NEW paragraph (similarity {p['context']['similarity']}), for context:*", "",
                            quote(p["context"]["text"]), ""]
                else:
                    out += ["*No similar NEW paragraph.*", ""]
            else:  # split / merged
                out += ["**OLD:**", "", quote(p["old_text"]), "", "**NEW:**", "", quote(p["new_text"]), ""]
            out += ["**Label:** ", "", "**Note (optional):** ", ""]
        (ROOT / "docs" / f"materiality-labels-{split}.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    counts = defaultdict(lambda: [0, 0])
    for p in chosen:
        counts[p["stratum"]][p["split"] == "test"] += 1
    print("population:", population)
    print("sampled (dev, test):", {k: tuple(v) for k, v in counts.items()},
          "| companies:", len({p["company"] for p in chosen}))


if __name__ == "__main__":
    main()
