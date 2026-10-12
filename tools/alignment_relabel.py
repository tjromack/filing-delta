"""Second-pass sheet: re-judge the 'Y' and '?' pairs under the instance criterion (FD-DEC 018, decided 2026-10-12).

    python tools/alignment_relabel.py      # writes docs/alignment-relabel.md

The first-pass labels stay in docs/alignment-labeling.md. tools/eval_alignment.py reads both: a second-pass label
replaces the first for its item, with T counted as "not the same disclosure".
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def first_pass() -> dict[str, str]:
    text = (ROOT / "docs" / "alignment-labeling.md").read_text(encoding="utf-8")
    out = {}
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        m = re.search(r"\*\*Label:\*\*[ \t]*([YNyn?])", block)
        if m:
            out[block.split(" ", 1)[0]] = m.group(1).upper()
    return out


def main() -> None:
    items = json.loads((ROOT / "tests" / "golden" / "alignment_sample.json").read_text(encoding="utf-8"))["items"]
    lab = first_pass()
    todo = [it for it in items if lab.get(it["id"]) in ("Y", "?")]
    cut = lambda s: s if len(s) <= 1500 else s[:1500] + " […cut]"  # noqa: E731
    out = [
        "# Alignment relabel: same instance, or just the same template?",
        "",
        "These are the pairs you marked **Y** or **?** in the first pass. The question is now narrower: is the NEW "
        "paragraph **the same instance**, meaning the same subject or event, revised?",
        "",
        "- **Y**: same instance. The same risk reworded; the same metric, segment, region or matter updated with new "
        "numbers or dates; the same paragraph expanded or shortened. *e.g. \"Net sales rose 5% in 2024\" → \"Net sales "
        "rose 3% in 2025\".*",
        "- **T**: same *template*, different instance. The same kind of sentence about a different region, segment, "
        "product, event or fact. *e.g. \"Sales in Europe rose 4%\" → \"Sales in Latin America rose 6%\"; \"In 2019 we "
        "sold business A\" → \"In 2020 we exited business B\".*",
        "- **N**: on a second read, not related at all.",
        "- **?**: still can't tell.",
        "",
        "Rule of thumb: if the NEW text appeared in the filing and the OLD one didn't, would a reader call it *new "
        "information*? If yes, it's **T** (or N). If it's the old information updated, it's **Y**.",
        "",
    ]
    for it in todo:
        out += [f"## {it['id']} · {it['company']} · {it['section']} · {it['old_date']} → {it['new_date']} · first pass:"
                f" {lab[it['id']]}", "",
                "**OLD:**", "", "> " + cut(it["old_text"]).replace("\n\n", "\n>\n> "), "",
                "**NEW:**", "", "> " + cut(it["new_text"]).replace("\n\n", "\n>\n> "), "",
                "**Label:** ", "", "**Note (optional):** ", ""]
    (ROOT / "docs" / "alignment-relabel.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"{len(todo)} pairs -> docs/alignment-relabel.md")


if __name__ == "__main__":
    main()
