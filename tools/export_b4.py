"""Export the 60 labeled QA pairs for Build 4's benchmark (M9, FD-DEC 039), and validate them.

    python tools/export_b4.py      # -> export/b4-finance-qa.jsonl + docs/b4-export.md; exits non-zero if invalid

Each item: the question and who wrote it; the label (answerable or not, gold answers); every evidence span with its
filing, section, exact offsets, exact text and the sha256 of the section text the offsets index; and the label's
provenance (both jurors' verdicts and, where they split, Trevor's decision; FD-DEC 031). Built only from committed
records (tests/golden/qa_questions.json, qa_key.json, qa_jury.json) and the section texts. Validation is twofold:
schemas/b4-qa-item.schema.json, then every span re-read from its section and its hash re-checked.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.qa.guard import load_catalog as catalog  # noqa: E402

OUT = ROOT / "export" / "b4-finance-qa.jsonl"
SCHEMA = ROOT / "schemas" / "b4-qa-item.schema.json"
COVERAGE = ("SEC filings of 11 companies (Apple, Coca-Cola, Netflix, Walmart, Pfizer, Ford, Weyco Group, Berkshire "
            "Hathaway, JPMorgan Chase, Exxon Mobil, General Electric): 10-K Item 1A and Item 7 for fiscal years "
            "2018-2025, and 10-Q Part I Item 2 and Part II Item 1A filed January 2025 to September 2026")
TEXT_BASIS = ("char_start/char_end index filing-delta's canonical section text, data/sections/<accession>/<section>.txt, "
              "rebuilt by `filing-delta parse` from the data release; section_sha256 pins that text, and text is "
              "the exact slice")
JURORS = ("claude-opus-5-5", "claude-fable-5-1")


def golden(name: str) -> dict | list:
    return json.loads((ROOT / "tests" / "golden" / name).read_text(encoding="utf-8"))


def build() -> list[dict]:
    qs = {q["id"]: q for q in golden("qa_questions.json")["questions"]}
    key = {k["id"]: k for k in golden("qa_key.json")["key"]}
    jury = {r["id"]: r for r in golden("qa_jury.json")}
    release = json.loads((ROOT / "release" / "manifest.json").read_text(encoding="utf-8"))["tag"]
    with (ROOT / "corpus" / "manifest.csv").open(encoding="utf-8") as f:
        manifest = {r["accession"]: r for r in csv.DictReader(f)}
    filings = {f.accession: f for f in catalog(ROOT)}
    texts: dict[str, str] = {}
    items = []
    for qid in sorted(qs):
        q, k, j = qs[qid], key[qid], jury[qid]
        evidence = []
        for s in k["spans"]:
            acc, sec = s["key"].split("|")
            if s["key"] not in texts:
                texts[s["key"]] = (ROOT / "data" / "sections" / acc / f"{sec}.txt").read_text(encoding="utf-8")
            t, m, f = texts[s["key"]], manifest[acc], filings[acc]
            evidence.append({"cik": int(m["cik"]), "company": m["company"], "form": m["form"],
                             "fiscal_year": f.fiscal_year, "fiscal_period": f.fiscal_period, "period_end": f.period_end,
                             "accession": acc, "url": m["url"], "section": sec,
                             "section_sha256": hashlib.sha256(t.encode("utf-8")).hexdigest(),
                             "char_start": s["start"], "char_end": s["end"], "text": t[s["start"]:s["end"]]})
        labelers = [{"kind": "model", "id": m, "state": j["jurors"][m]["state"], "answer": j["jurors"][m]["answer"],
                     "reason": j["jurors"][m]["reason"]} for m in JURORS]
        method = "jury_agreed" if k["provenance"] == "jury_agreed" else "human_adjudicated"
        if method == "human_adjudicated":
            choice = re.search(r"\((\w+)\)", k["provenance"])
            labelers.append({"kind": "human", "id": "trevor", "state": k["state"], "answer": (k["answers"] or [""])[0],
                             "reason": f"Decided after reviewing both jurors' labels; chose {choice.group(1) if choice else 'own label'}."})
        answerable = k["state"] == "answerable"
        items.append({
            "schema_version": "1.0", "id": "fd-qa-" + qid[2:],
            "corpus": {"name": "filing-delta", "domain": "finance", "coverage": COVERAGE, "data_release": release,
                       "text_basis": TEXT_BASIS},
            "question": {"text": q["question"], "author": "human_written" if q["author"] == "trevor" else "model_drafted",
                         "category": q["category"], "author_note": q.get("author_note")},
            "label": {"answerable": answerable, "state": k["state"],
                      "gold_answers": [a for a in k["answers"] if a] if answerable else []},
            "evidence": evidence if answerable else [],
            "provenance": {"method": method, "labelers": labelers, "note": k.get("note"),
                           "decision": "filing-delta FD-DEC 031 (jury key) and FD-DEC 028 (question set)"},
        })
    return items


def validate(items: list[dict]) -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker

    v = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=FormatChecker())
    errors = [f"{it['id']}: {e.message} at {'/'.join(map(str, e.absolute_path))}" for it in items
              for e in v.iter_errors(it)]
    if len({it["id"] for it in items}) != len(items):
        errors.append("duplicate ids")
    for it in items:                       # every span re-read from its section; every hash re-checked
        for ev in it.get("evidence") or []:
            p = ROOT / "data" / "sections" / str(ev.get("accession")) / f"{ev.get('section')}.txt"
            if not isinstance(ev.get("char_start"), int) or not isinstance(ev.get("char_end"), int) or not p.exists():
                errors.append(f"{it.get('id')}: evidence doesn't name a stored section and integer offsets")
                continue
            t = p.read_text(encoding="utf-8")
            if hashlib.sha256(t.encode("utf-8")).hexdigest() != ev["section_sha256"]:
                errors.append(f"{it['id']}: section_sha256 mismatch for {ev['accession']} {ev['section']}")
            if t[ev["char_start"]:ev["char_end"]] != ev["text"] or ev["char_end"] <= ev["char_start"]:
                errors.append(f"{it['id']}: evidence text isn't the slice it claims")
    return errors


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    items = build()
    errors = validate(items)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(it, ensure_ascii=False, sort_keys=True) + "\n" for it in items),
                   encoding="utf-8", newline="\n")
    ans = [it for it in items if it["label"]["answerable"]]
    lines = ["# Build 4 export: finance QA items (M9)", "",
             f"`export/b4-finance-qa.jsonl`: **{len(items)} items**, one JSON object per line, schema "
             "`schemas/b4-qa-item.schema.json` (version 1.0, proposed here for Build 4; FD-DEC 039). Generated by "
             "`tools/export_b4.py` from committed records; `tools/reproduce.py` regenerates it byte for byte.", "",
             f"- Coverage: {COVERAGE}.",
             f"- Answerable: {len(ans)}, with {sum(len(it['evidence']) for it in ans)} evidence spans in all; not "
             f"answerable: {len(items) - len(ans)}.",
             f"- Question authors: {dict(Counter(it['question']['author'] for it in items))}.",
             f"- Label provenance: {dict(Counter(it['provenance']['method'] for it in items))}. Jury-agreed labels are "
             "model-built (two models agreeing, FD-DEC 031); the human-adjudicated ones are where they split.",
             f"- Categories: {dict(sorted(Counter(it['question']['category'] for it in items).items()))}.",
             f"- Evidence by section: {dict(sorted(Counter(ev['section'] for it in ans for ev in it['evidence']).items()))}.",
             "", "## Validation", "",
             f"- JSON Schema (draft 2020-12, with format checks) and a re-read of every span from its section text, "
             f"with each section's sha256 re-checked: **{'all items valid' if not errors else f'{len(errors)} errors'}**."]
    lines += [f"  - {e}" for e in errors[:50]]
    lines += ["", "## For Build 4", "",
              "- Spans are sentence-level: the answer key marks the sentences that answer a question, and a gold span "
              "is a whole sentence, not a minimal phrase.",
              "- `gold_answers` holds each labeler's short answer where the jurors agreed (two phrasings of one answer), "
              "or the human's answer where they split.",
              "- An unanswerable item has no evidence. Its category says why: outside coverage, not in the corpus, "
              "advice or prediction, undisclosed, or (for human-written questions) `trevor`.",
              "- The 48 model-drafted questions were drawn from passages picked by a deterministic sampler and are "
              "easier for models than the 12 human-written ones (filing-delta FD-DEC 028, 032)."]
    (ROOT / "docs" / "b4-export.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[2:12]))
    if errors:
        raise SystemExit(f"{len(errors)} validation errors")


if __name__ == "__main__":
    main()
