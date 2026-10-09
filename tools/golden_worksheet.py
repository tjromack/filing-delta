"""Generate docs/golden-review-worksheet.md: Trevor's checklist for confirming the golden boundaries.

    python tools/golden_worksheet.py

Reads tests/golden/sections.json + corpus/manifest.csv. One entry per golden section, hardest first, with search
strings for EDGAR and blank fields for the verdict and notes. Re-running overwrites the file, so finish your notes
before re-generating.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = {"10K_1A": "10-K Item 1A (Risk Factors)", "10K_7": "10-K Item 7 (MD&A)",
         "10Q_P1_2": "10-Q Part I Item 2 (MD&A)", "10Q_P2_1A": "10-Q Part II Item 1A (Risk Factors)"}
# Where the parser had to work hardest; read these properly. Everything else is a routine linear layout.
HARD = {("jpm-20251231.htm", "10K_7"), ("xom-20251231.htm", "10K_7"), ("ge-20251231.htm", "10K_1A"),
        ("ge-20251231.htm", "10K_7"), ("ge10-k2018.htm", "10K_1A"), ("ge10-k2018.htm", "10K_7"),
        ("jpm-20260630.htm", "10Q_P1_2"), ("brka-20260630.htm", "10Q_P1_2")}
WHAT_TO_CHECK = {
    "full": "Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.",
    "pointer": "The text is the filing's entire statement for this item (a reference to another filing). Nothing more "
               "is printed under this heading in the filing.",
    "absent": "Open the filing's Part II. Confirm it goes from Item 1 straight to Item 2 (or later) with no Item 1A "
              "and no 'Risk Factors' heading.",
}


def snippet(text: str, n: int = 60) -> str:
    """A search string from the first block only (Ctrl+F can't match across a heading/paragraph break)."""
    s = " ".join(text.split("\n\n")[0].split())
    if len(s) <= n:
        return s
    return s[:n].rsplit(" ", 1)[0]


def tail_snippet(text: str, n: int = 60) -> str:
    """A search string from the last block only."""
    s = " ".join(text.split("\n\n")[-1].split())
    if len(s) <= n:
        return s
    return s[-n:].split(" ", 1)[1] if " " in s[-n:] else s[-n:]


def main() -> None:
    golden = json.loads((ROOT / "tests" / "golden" / "sections.json").read_text(encoding="utf-8"))
    urls = {r["accession"]: r["url"] for r in csv.DictReader((ROOT / "corpus" / "manifest.csv").open(encoding="utf-8"))}
    golden.sort(key=lambda e: ((e["document"], e["section"]) not in HARD, e["outcome"] != "failed",
                               e["company"], e["report_date"], e["section"]))
    out = [
        "# Golden review worksheet",
        "",
        "Fill in **Verdict** for each entry with one of `CONFIRMED`, `WRONG-START`, `WRONG-END`, `WRONG-BOTH`,",
        "`WRONG-KIND` or `UNSURE`. Write **Notes** in your own words: what you saw, and where in the filing. The",
        "process is in the chat; the boundary context for each entry is in `docs/golden-review.md`.",
        "",
        "Search tips: EDGAR pages are long. Use Ctrl+F with the search strings below. If a string doesn't hit, search a",
        "shorter piece of it: curly quotes, dashes and line breaks often differ between the filing and the extracted",
        "text.",
        "",
    ]
    for n, e in enumerate(golden, 1):
        tier = "HARD" if (e["document"], e["section"]) in HARD else "routine"
        out += [
            f"## {n}. {e['company']} · {e['form']} · period {e['report_date']} · {LABEL[e['section']]} · {tier}",
            "",
            f"- Filing: <{urls[e['accession']]}>",
            f"- Parser says: `{e['outcome']}` / `{e['form_kind']}` · {e['chars']:,} characters"
            + (f" · reasons: `{', '.join(e['reasons'])}`" if e["reasons"] else ""),
            f"- Check: {WHAT_TO_CHECK.get(e['form_kind'], '')}" if e["outcome"] != "failed" else
            "- Check: the filing's Item 7 says the MD&A is incorporated by reference from a separate exhibit "
            "(the annual 'Financial Report'), so there's no MD&A text in this document to extract.",
        ]
        if e["chars"] and e["form_kind"] == "full":
            out += [f"- Search for the **start**: `{snippet(e['head'])}`",
                    f"- Search for the **end**: `{tail_snippet(e['tail'])}`"]
        elif e["chars"]:
            out += [f"- Search for the statement: `{snippet(e['head'])}`"]
        out += [
            "",
            "**Verdict:** ",
            "",
            "**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes",
            "",
            "**Notes:** ",
            "",
        ]
    out += ["## Overall", "", "**Calls you'd change** (GE's MD&A excluding 'Other Financial Data'; run-in headings "
            "kept, bare title lines dropped; tables as cell text):", "", "**Time spent:** ", ""]
    (ROOT / "docs" / "golden-review-worksheet.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"{len(golden)} entries -> docs/golden-review-worksheet.md")


if __name__ == "__main__":
    main()
