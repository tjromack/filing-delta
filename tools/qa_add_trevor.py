"""Append Trevor's own questions to the QA set and assign blind ids (M6, FD-DEC 028).

    python tools/qa_add_trevor.py      # reads docs/qa-questions-trevor.md -> tests/golden/qa_questions.json

Each numbered line "N. - question // optional note" becomes an item with author "trevor" and intent "unknown"
(Trevor labels it like any other). Then every question gets an id QA01..QAnn in sha256 order of its text, so the
labeling order mixes authors and categories. Refuses to run twice or once labels exist.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "golden" / "qa_questions.json"


def main() -> None:
    data = json.loads(OUT.read_text(encoding="utf-8"))
    if any("id" in q for q in data["questions"]):
        raise SystemExit("ids are already assigned; Trevor's questions were already added.")
    sheet = (ROOT / "docs" / "qa-questions-trevor.md").read_text(encoding="utf-8")
    mine = []
    for m in re.finditer(r"(?m)^\d+\.\s*-\s*(.+?)\s*$", sheet):
        q, _, note = m.group(1).partition("//")
        if q.strip():
            mine.append({"author": "trevor", "intent": "unknown", "category": "trevor", "question": q.strip(),
                         "source": None, "author_note": note.strip() or None})
    if len(mine) < 12:
        raise SystemExit(f"only {len(mine)} questions found in docs/qa-questions-trevor.md; 12 or more expected.")
    qs = data["questions"] + mine
    for n, q in enumerate(sorted(qs, key=lambda q: hashlib.sha256(q["question"].encode("utf-8")).hexdigest()), 1):
        q["id"] = f"QA{n:02d}"
    data["questions"] = sorted(qs, key=lambda q: q["id"])
    data["trevor_added"] = len(mine)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"added {len(mine)} of Trevor's questions; {len(qs)} in all, ids QA01..QA{len(qs):02d}")


if __name__ == "__main__":
    main()
