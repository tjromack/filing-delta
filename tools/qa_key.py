"""Assemble the QA answer key from the jury and Trevor's review (M6, FD-DEC 031). Run once, before any QA run.

    python tools/qa_key.py      # tests/golden/qa_jury.json + data/qa/labels-review.json -> tests/golden/qa_key.json

Where the jurors agree, their label is the key: for answerable, the union of both jurors' answering sentences (the
key says where the answer is, and either juror's sentences count). Where they disagree, Trevor's decision is the key.
Every entry records its provenance. Refuses to overwrite an existing key.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "golden" / "qa_key.json"
STATE = {"A": "answerable", "N": "not_answerable", "U": "unsure", "W": "wrong_filing", "R": "reject"}


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"{OUT.name} exists; the key is fixed once written.")
    jury = json.loads((ROOT / "tests" / "golden" / "qa_jury.json").read_text(encoding="utf-8"))
    review = json.loads((ROOT / "data" / "qa" / "labels-review.json").read_text(encoding="utf-8"))
    key = []
    for r in jury:
        a, b = r["jurors"].values()
        if r["agree"]:
            spans = []
            for s in a["spans"] + b["spans"]:
                if s not in spans:
                    spans.append(s)
            key.append({"id": r["id"], "state": a["state"], "spans": sorted(spans, key=lambda s: (s["key"], s["start"])),
                        "answers": [a["answer"], b["answer"]], "provenance": "jury_agreed", "note": None})
        else:
            v = review.get(r["id"])
            if not v or not v.get("state"):
                raise SystemExit(f"{r['id']}: a jury disagreement without Trevor's decision")
            key.append({"id": r["id"], "state": STATE[v["state"]], "spans": v["spans"], "answers": [v["answer"]],
                        "provenance": f"trevor_adjudicated ({v['choice']})", "note": v.get("note") or None,
                        "decided": v["at"]})
    OUT.write_text(json.dumps({"built": "2026-10-20", "rule": "FD-DEC 031", "key": key}, indent=1,
                              ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    from collections import Counter
    print(f"{len(key)} entries -> {OUT.relative_to(ROOT)}:", dict(Counter(k["state"] for k in key)),
          dict(Counter(k["provenance"].split(" ")[0] for k in key)))


if __name__ == "__main__":
    main()
