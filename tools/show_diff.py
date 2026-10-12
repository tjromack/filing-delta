"""Print a diff record readably: one line per op, with text snippets.

    python tools/show_diff.py data/diffs/<file>.json [--status added,removed] [--edges N] [--width 140]

--edges N shows only the first and last N ops (where boundary errors would show up).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--status", default="")
    ap.add_argument("--edges", type=int, default=0)
    ap.add_argument("--width", type=int, default=140)
    a = ap.parse_args()
    rec = json.loads(Path(a.file).read_text(encoding="utf-8"))
    sec = ROOT / "data" / "sections"
    told = (sec / rec["old"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
    tnew = (sec / rec["new"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
    print(rec["company"], rec["section"], rec["old"]["report_date"], "->", rec["new"]["report_date"],
          rec.get("counts"), "churn", rec.get("churn"), rec.get("flags"))
    ops = rec["ops"]
    if a.status:
        ops = [o for o in ops if o["status"] in a.status.split(",")]
    if a.edges:
        ops = ops[: a.edges] + ([{"status": "...."}] if len(ops) > 2 * a.edges else []) + ops[-a.edges:] \
            if len(ops) > 2 * a.edges else ops
    w = a.width
    for o in ops:
        if o["status"] == "....":
            print("   ....")
            continue
        def snip(units, text, ids):
            return " | ".join(" ".join(text[units[i][1]:units[i][2]].split())[:w] for i in ids)
        old = snip(rec["old_units"], told, o["old"])
        new = snip(rec["new_units"], tnew, o["new"])
        kinds = "/".join(sorted({rec["old_units"][i][0] for i in o["old"]} | {rec["new_units"][j][0] for j in o["new"]}))
        tag = f"{o['status']:9} {kinds[:9]:9} sim={o['similarity']:.2f}"
        if o["status"] in ("added",):
            print(f"{tag}  + {new}")
        elif o["status"] in ("removed",):
            print(f"{tag}  - {old}")
        elif o["status"] == "unchanged":
            print(f"{tag}  = {new[:80]}")
        else:
            print(f"{tag}  - {old}\n{'':33}  + {new}")


if __name__ == "__main__":
    main()
