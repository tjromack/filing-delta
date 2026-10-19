"""Build the QA labeling pages (M6, FD-DEC 028), published as private artifacts.

    python tools/build_qa_label_app.py practice   # 3 worked items outside the set -> data/labeling/qa-practice.html
    python tools/build_qa_label_app.py set        # the 60 -> data/labeling/qa-labeler.html

Each item embeds the full text of every section in its scope (the frozen pipeline's deterministic scoping, not its
retrieval), so a gold span can come from anywhere in it; candidates proposed by the system's own search would make
retrieval recall circular. Drafted answerable items open at the passage they were drafted from. No system answer,
retrieval result, author or intended category is shown.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.qa.index import catalog  # noqa: E402
from filing_delta.qa.prompt import SECTION_LABEL, filing_label  # noqa: E402
from filing_delta.qa.scope import ALIASES, scope  # noqa: E402

PRACTICE = [
    {"id": "P1", "question": "What drove Netflix's streaming revenue increase in 2024?",
     "worked": "Answerable. Search for \"increased 16%\" or \"primarily due\".\nSelect: \"primarily due to the growth "
               "in average paying memberships and price increases, partially offset by unfavorable changes in foreign "
               "exchange rates\" and press S.\nShort answer: Growth in paying memberships and price increases, partly "
               "offset by currency. Then press A."},
    {"id": "P2", "question": "What does Apple's 2023 10-K say Tim Cook's salary was?",
     "worked": "Not answerable. Search \"salary\" and \"Cook\": nothing in these sections gives his pay. Executive "
               "pay is in the proxy statement, which isn't in this corpus. Press N. Searching to confirm it's "
               "absent is the real work on items like this."},
    {"id": "P3", "question": "What new risks did Coca-Cola add between its 2022 and 2023 10-Ks?",
     "worked": "Answerable, with two spans in the 2023 filing (open the fiscal 2023 tab).\nSearch \"sustainability\": "
               "select the sentence about increasing sustainability regulatory requirements, press S.\nSearch \"Pillar "
               "Two\": select the sentence introducing it, press S.\nShort answer: Sustainability regulation, and the "
               "OECD Pillar Two global minimum tax. Press A. Both versions of a reworded risk can appear; for \"what "
               "was added\", pick text that is new in the later filing."},
]


def build_items(questions: list[dict]) -> tuple[list[dict], dict]:
    cat = catalog(ROOT)
    by_acc = {f.accession: f for f in cat}
    sections: dict[str, str] = {}
    items = []
    for q in questions:
        s = scope(q["question"], cat)
        keys, labels = [], []
        if not s.abstain:
            for f in s.filings:
                fl = filing_label(ALIASES[f.cik][0], f.form, f.fiscal_year, f.fiscal_period, f.period_end)
                labels.append(fl)
                for sec in s.sections:
                    if sec in f.sections:
                        k = f"{f.accession}|{sec}"
                        keys.append(k)
                        sections[k] = (ROOT / "data" / "sections" / f.accession / f"{sec}.txt").read_text(
                            encoding="utf-8")
        item = {"id": q["id"], "question": q["question"], "sections": keys,
                "scope_label": ("Filing text below: " + "; ".join(labels)) if labels else
                               "No filing text is shown for this question."}
        src = q.get("source")
        if src and f"{src['accession']}|{src['section']}" in keys:
            item["start"] = {"key": f"{src['accession']}|{src['section']}", "start": src["start"], "end": src["end"]}
        if q.get("worked"):
            item["worked"] = q["worked"]
        items.append(item)
    labels = {}
    for k in sections:
        acc, sec = k.split("|")
        f = by_acc[acc]
        labels[k] = f"{f.form} fiscal {f.fiscal_year}{' ' + f.fiscal_period if f.form == '10-Q' else ''} · " \
                    f"{SECTION_LABEL[sec].split(',')[0] if sec.startswith('10K') else SECTION_LABEL[sec].split(',', 2)[0] + ' ' + SECTION_LABEL[sec].split(',')[1].strip()}"
    return items, {"sections": sections, "section_labels": labels}


def main() -> None:
    mode = sys.argv[1]
    if mode == "practice":
        items, extra = build_items(PRACTICE)
        coll, dest, practice = "practice", "qa-practice.html", True
    else:
        data = json.loads((ROOT / "tests" / "golden" / "qa_questions.json").read_text(encoding="utf-8"))
        qs = data["questions"]
        assert all("id" in q for q in qs), "assign ids first (tools/qa_add_trevor.py)"
        items, extra = build_items(sorted(qs, key=lambda q: q["id"]))
        coll, dest, practice = "qa", "qa-labeler.html", False
    tpl = (ROOT / "tools" / "qa_label_template.html").read_bytes()
    built = hashlib.sha256(tpl).hexdigest()[:6]          # which page version the labeler is looking at
    payload = json.dumps({"items": items, **extra, "collection": coll, "practice": practice, "built": built},
                         ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "tools" / "qa_label_template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    if practice:
        html = html.replace("<title>Filing QA Labeler</title>", "<title>Filing QA Practice</title>", 1)
    out = ROOT / "data" / "labeling" / dest
    out.write_text(html, encoding="utf-8", newline="\n")
    print(f"{mode}: {len(items)} items, {len(extra['sections'])} sections -> {out.relative_to(ROOT)} "
          f"({len(html.encode('utf-8')) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
