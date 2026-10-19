"""Claude's drafted questions for the QA set (M6, FD-DEC 028), written 2026-10-19 before Trevor labels anything.

    python tools/qa_drafted.py     # -> tests/golden/qa_questions.json (refuses to overwrite once labels exist)

Answerable drafts cite the pool passage they were written from (tools/qa_draft_pool.py) or, for change questions,
a Risk Factors addition Trevor labeled material in the M4 blind test set. That source is provenance only: the gold
span and gold answer are Trevor's. Unanswerable drafts were checked against the scoped section text by keyword
before inclusion. Trevor's own questions are appended by tools/qa_add_trevor.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "golden" / "qa_questions.json"

# (pool passage index D01..D33, category, question)
FROM_POOL = [
    ("D02", "risk_presence", "According to JPMorgan's 2021 10-K, how could regulation outside the U.S. affect its "
                             "operations and legal entity structure?"),
    ("D03", "lookup", "Which agencies set JPMorgan's capital requirements, according to its 2020 10-K, and what "
                      "international framework do the U.S. rules generally follow?"),
    ("D04", "risk_presence", "Does Coca-Cola's 2021 10-K discuss product labeling or warning requirements as a risk, "
                             "and what effect does it say they could have?"),
    ("D05", "lookup", "How does Coca-Cola's 2025 10-K define concentrate sales volume?"),
    ("D07", "lookup", "What does Exxon's 2024 10-K say about inflation trends and central bank interest rates?"),
    ("D08", "lookup", "How does Exxon's Q3 2025 10-Q define earnings excluding Identified Items?"),
    ("D10", "lookup", "How does Ford's 2022 10-K describe the difference between its contribution costs and "
                      "structural costs?"),
    ("D13", "risk_presence", "What does GE's 2024 10-K say about whether its cyber insurance will cover "
                             "cybersecurity liabilities?"),
    ("D15", "lookup", "What strategic risks does GE's 2023 10-K list, including anything about its planned "
                      "separation?"),
    ("D17", "risk_presence", "What risks does Pfizer's 2020 10-K describe around its cost-reduction and productivity "
                             "initiatives?"),
    ("D18", "figure", "How much of Pfizer's revenue did its Russia and Ukraine subsidiaries represent, according to "
                      "its 2023 10-K?"),
    ("D19", "figure", "What drove the decline in Walmart International's gross profit rate in fiscal 2023?"),
    ("D20", "risk_presence", "What does Walmart's fiscal 2025 10-K say about the Competition Commission of India "
                             "investigation into Flipkart?"),
    ("D21", "figure", "What was Walmart's working capital deficit at the end of Q2 fiscal 2026, and why did it "
                      "increase?"),
    ("D22", "lookup", "Does Weyco have long-term contracts with its foreign manufacturers, according to its 2019 "
                      "10-K?"),
    ("D23", "lookup", "According to Weyco's 2023 10-K, why was its inventory at peak levels at the end of 2022?"),
    ("D25", "figure", "What drove the growth in Apple's research and development expense in 2021?"),
    ("D26", "lookup", "Why was Apple's effective tax rate lower than the statutory rate in the second quarter of "
                      "fiscal 2025?"),
    ("D28", "risk_presence", "What privacy-related risks does Netflix's 2025 10-K describe for its international "
                             "operations?"),
    ("D29", "figure", "How much of Netflix's content obligations at the end of 2020 were not on its balance sheet?"),
    ("D30", "risk_presence", "Does Netflix's 2019 10-K mention social media in its marketing, and what risk does it "
                             "tie to its marketing channels?"),
    ("D31", "figure", "Which reporting unit does Berkshire's 2025 10-K single out in its goodwill impairment review, "
                      "and what were that unit's estimated fair value and carrying value?"),
    ("D32", "lookup", "Who does Berkshire's 2022 10-K say would replace Warren Buffett if a replacement were needed?"),
    ("D33", "figure", "What were the pre-tax earnings of Berkshire's retail group in 2019?"),
]
# (M4 test item whose added text Trevor labeled material, question)
CHANGE = [
    ("M116", "What did Coca-Cola add to its risk factors about COVID-19 and its supply chain between its 2020 and "
             "2021 10-Ks?"),
    ("M113", "What new ESG-related risk text did Pfizer add between its 2021 and 2022 10-Ks?"),
    ("M088", "What did Berkshire add about climate change between its 2020 and 2021 10-Ks?"),
    ("M131", "What did Ford add about electric vehicle adoption between its 2022 and 2023 10-Ks?"),
]
UNANSWERABLE = [
    ("outside_coverage", "What did Apple's 2016 10-K say about the iPhone 7 launch?"),
    ("outside_coverage", "What risks did Netflix list in its Q2 2024 10-Q?"),
    ("outside_coverage", "What does GE's 2026 10-K say about aerospace orders?"),
    ("outside_coverage", "What did Ford's 2017 10-K say about autonomous vehicles?"),
    ("not_in_corpus", "What does Microsoft's 2023 10-K say about its AI investments?"),
    ("not_in_corpus", "What risks does Tesla describe about its Gigafactories in its 2024 10-K?"),
    ("not_in_corpus", "How did Amazon describe AWS growth in its 2022 10-K?"),
    ("advice", "Should I buy JPMorgan stock after reading its 2025 10-K?"),
    ("advice", "Will Coca-Cola's dividend increase next year?"),
    ("advice", "Is Pfizer stock undervalued based on its 2024 10-K?"),
    ("advice", "Will Walmart's revenue grow in fiscal 2027?"),
    ("undisclosed", "What does Apple's 2024 10-K say its iPhone unit sales were in Greater China?"),
    ("undisclosed", "How many Netflix members did Netflix have in India according to its 2023 10-K?"),
    ("undisclosed", "How much did Coca-Cola spend on Super Bowl advertising according to its 2022 10-K?"),
    ("undisclosed", "What does JPMorgan's 2023 10-K say Jamie Dimon's bonus was?"),
    ("undisclosed", "What price per pair does Weyco's 2024 10-K say it paid its Chinese manufacturers?"),
    ("undisclosed", "What does Exxon's 2023 10-K say its breakeven oil price is for its Guyana projects?"),
    ("undisclosed", "How many F-150 Lightning trucks did Ford sell in Norway according to its 2023 10-K?"),
    ("undisclosed", "What profit margin does Pfizer's 2024 10-K report for Comirnaty?"),
    ("undisclosed", "How many employees did Walmart have in China according to its fiscal 2024 10-K?"),
]


def main() -> None:
    if OUT.exists() and any(q.get("label") for q in json.loads(OUT.read_text(encoding="utf-8"))["questions"]):
        raise SystemExit(f"{OUT.name} holds labels; refusing to overwrite.")
    pool = json.loads((ROOT / "data" / "qa" / "draft_pool.json").read_text(encoding="utf-8"))
    sample = {m["id"]: m for m in json.loads((ROOT / "tests" / "golden" / "materiality_sample.json")
                                              .read_text(encoding="utf-8"))["items"]}
    qs = []
    for d, cat, q in FROM_POOL:
        p = pool[int(d[1:]) - 1]
        qs.append({"author": "claude", "intent": "answerable", "category": cat, "question": q,
                   "source": {"kind": "pool", "ref": d, "accession": p["accession"], "section": p["section"],
                              "start": p["start"], "end": p["end"]}})
    for mid, q in CHANGE:
        m = sample[mid]
        rec = json.loads((ROOT / "data" / "diffs" / m["file"]).read_text(encoding="utf-8"))
        spans = [rec["new_units"][j][1:3] for j in rec["ops"][m["op"]]["new"]]
        qs.append({"author": "claude", "intent": "answerable", "category": "change", "question": q,
                   "source": {"kind": "m4_material_addition", "ref": mid, "accession": rec["new"]["accession"],
                              "section": rec["section"], "start": spans[0][0], "end": spans[-1][1]}})
    for cat, q in UNANSWERABLE:
        qs.append({"author": "claude", "intent": "unanswerable", "category": cat, "question": q, "source": None})
    OUT.write_text(json.dumps({"drafted": "2026-10-19", "questions": qs}, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"{len(qs)} drafted questions -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
