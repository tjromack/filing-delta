"""Copy labels saved in the labeling page's db into docs/materiality-labels-test.md (the committed record).

    python tools/import_app_labels.py <dir>     # <dir> holds labels/<id>.json, as ArtifactData list --out_dir writes

Fills **Label:** with "M code" / "C code" / "U" and the note, for every item the page labeled. It refuses to overwrite
a different label already in the sheet, and reports which items are still unlabeled.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    src = Path(sys.argv[1])
    labels = {}
    for f in sorted(src.rglob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        body = doc.get("data", doc)
        ident = doc.get("id", f.stem)
        if re.fullmatch(r"M\d{3}", ident) and body.get("label") in ("M", "C", "U"):
            labels[ident] = body
    sheet = ROOT / "docs" / "materiality-labels-test.md"
    blocks = re.split(r"(?m)^(?=## M\d{3} )", sheet.read_text(encoding="utf-8"))
    filled, conflicts, missing = 0, [], []
    for k, b in enumerate(blocks):
        m = re.match(r"## (M\d{3}) ", b)
        if not m:
            continue
        ident = m.group(1)
        if ident not in labels:
            missing.append(ident)
            continue
        v = labels[ident]
        want = (v["label"] + (" " + v["code"] if v.get("code") else "")).strip()
        cur = re.search(r"\*\*Label:\*\*[ \t]*(.*)", b).group(1).strip()
        if cur and cur != want:
            conflicts.append(f"{ident}: sheet has '{cur}', page has '{want}'")
            continue
        b = re.sub(r"\*\*Label:\*\*[ \t]*.*", lambda _: f"**Label:** {want}", b, count=1)
        if v.get("note"):
            b = re.sub(r"\*\*Note \(optional\):\*\*[ \t]*.*", lambda _: f"**Note (optional):** {v['note']}", b, count=1)
        blocks[k] = b
        filled += 1
    if conflicts:
        raise SystemExit("Refusing to overwrite differing labels:\n  " + "\n  ".join(conflicts))
    sheet.write_text("".join(blocks), encoding="utf-8", newline="\n")
    print(f"filled {filled}; still unlabeled: {len(missing)} {missing[:10]}")


if __name__ == "__main__":
    main()
