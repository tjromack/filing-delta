"""Build the keyboard labeling page for the materiality TEST set (published as a private artifact).

    python tools/build_label_app.py            # blind test set -> data/labeling/risk-factor-labeler.html
    python tools/build_label_app.py recheck    # disagreements, with the classifier's context -> label-recheck.html

The page embeds the 122 test items exactly as docs/materiality-labels-test.md shows them (same inline diff, same
closest-paragraph context, no model output). Labels are saved one document per item in the artifact's `db`
(collection `labels`), from which they are read back into the markdown sheet (tools/import_app_labels.py).
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.classify.prompt import COSMETIC_CODES, MATERIAL_CODES  # noqa: E402

LABEL = {"10K_1A": "10-K Item 1A", "10Q_P2_1A": "10-Q Part II Item 1A"}


def diff_segments(a: str, b: str) -> list[list[str]]:
    """The sheet's inline diff as typed segments: eq / del / ins / gap (collapsed unchanged run)."""
    wa, wb = a.split(), b.split()
    out: list[list[str]] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if tag == "equal":
            run = wa[i1:i2]
            if len(run) > 40:
                out += [["eq", " ".join(run[:15])], ["gap", f"{len(run) - 30} unchanged words"],
                        ["eq", " ".join(run[-15:])]]
            else:
                out.append(["eq", " ".join(run)])
        if tag in ("delete", "replace"):
            out.append(["del", " ".join(wa[i1:i2])])
        if tag in ("insert", "replace"):
            out.append(["ins", " ".join(wb[j1:j2])])
    return out


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    sample = json.loads((ROOT / "tests" / "golden" / "materiality_sample.json").read_text(encoding="utf-8"))
    sheet = (ROOT / "docs" / "materiality-labels-test.md").read_text(encoding="utf-8")
    sheet_ids = re.findall(r"(?m)^## (M\d{3}) ", sheet)
    items = {m["id"]: m for m in sample["items"] if m["split"] == "test"}
    assert sheet_ids and set(sheet_ids) == set(items), "sheet and sample disagree"
    blind = {}
    for block in re.split(r"(?m)^## ", sheet)[1:]:
        mm = re.search(r"\*\*Label:\*\*[ \t]*([MCU])", block)
        if mm:
            blind[block.split(" ", 1)[0]] = mm.group(1)
    ids, restated = sheet_ids, {}
    if mode == "recheck":
        # The scored disagreements of the Sonnet test run (the published headline run), in the blind sheet's order.
        sys.path.insert(0, str(ROOT / "tools"))
        import run_materiality as rm
        res = {json.loads(l)["id"]: json.loads(l) for l in
               (ROOT / "data" / "classify" / "test-claude-sonnet-5-5.jsonl").read_text(encoding="utf-8").splitlines()}
        conv = {"M": "material", "C": "cosmetic"}
        ids = [i for i in sheet_ids if blind.get(i) in conv and res[i]["outcome"] == "ok"
               and res[i]["label"] in ("material", "cosmetic") and res[i]["label"] != conv[blind[i]]]
        for i in ids:
            ctx = rm.to_item(items[i])["context"]
            if ctx and ctx.get("kind") == "restated":
                restated[i] = ctx["passages"]
    out = []
    for i in ids:                       # the sheet's (blind) order
        m = items[i]
        rec = {"id": i, "company": m["company"].title() if m["company"].isupper() else m["company"],
               "section": LABEL[m["section"]], "old": m["old_date"], "new": m["new_date"], "status": m["status"]}
        if m["status"] in ("reworded", "moved"):
            rec["diff"] = diff_segments(m["old_text"], m["new_text"])
        elif m["status"] in ("added", "removed"):
            rec["text"] = m["new_text"] if m["status"] == "added" else m["old_text"]
            c = m.get("context")
            rec["context"] = {"side": c["side"], "sim": c["similarity"], "text": c["text"]} if c else None
        else:
            rec["oldText"], rec["newText"] = m["old_text"], m["new_text"]
        if mode == "recheck":
            rec["blind"] = blind[i]
            if i in restated:
                rec["restated"] = restated[i]
        out.append(rec)
    coll = "labels" if mode == "test" else "recheck"
    payload = json.dumps({"items": out, "material": MATERIAL_CODES, "cosmetic": COSMETIC_CODES, "collection": coll},
                         ensure_ascii=False).replace("</", "<\\/")
    template = (ROOT / "tools" / "label_app_template.html").read_text(encoding="utf-8")
    title, sub = ("Risk Factor Labeler", "test set") if mode == "test" else ("Label Recheck", "disagreements, with context")
    html = template.replace("/*__DATA__*/null", payload).replace("/*__TITLE__*/", title).replace("/*__SUBTITLE__*/", sub)
    dest = ROOT / "data" / "labeling" / ("risk-factor-labeler.html" if mode == "test" else "label-recheck.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8", newline="\n")
    print(f"{mode}: {len(out)} items ({len(restated)} with restatement context) -> {dest.relative_to(ROOT)} "
          f"({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
