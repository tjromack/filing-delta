"""The QA dev slice (M6): Claude-written questions, never part of the labeled 60, used only to tune the prompt.

    python tools/qa_dev.py            # calls the API for anything not yet recorded
    python tools/qa_dev.py --offline  # replays recorded responses only

Writes data/qa/dev.jsonl and prints, per question, the stage it ended at, the result and any verification problems.
There are no labels here. The point is to see whether answers verify, and why not when they don't.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.classify.model import Recorder  # noqa: E402
from filing_delta.cli import load_env  # noqa: E402
from filing_delta.qa.ask import ask  # noqa: E402
from filing_delta.qa.index import catalog  # noqa: E402

DEV = [
    "What does Apple's 2023 10-K say about its dependence on outsourcing partners in Asia?",
    "What drove Netflix's streaming revenue increase in 2024?",
    "What did JPMorgan's Q2 2026 10-Q say about commercial real estate exposure?",
    "How did Pfizer's 2022 10-K describe Comirnaty revenue?",
    "What new risks did Coca-Cola add between its 2022 and 2023 10-Ks?",
    "What does Walmart's fiscal 2025 10-K say about cybersecurity risks?",
    "What does Ford's 2024 10-K say about warranty and recall costs?",
    "What does Weyco's 2023 10-K say about its reliance on foreign manufacturers?",
    "What did Berkshire's 2022 10-K say about catastrophe losses in its insurance business?",
    "What does GE's 2025 10-K say about supply chain constraints?",
    "What does Apple's 2023 10-K say Tim Cook's salary was?",
    "Should I buy Netflix stock?",
    "What does Exxon's 2024 10-K say about the Pioneer acquisition?",
    "What did Walmart's Q1 2026 10-Q say about tariffs?",
    # Added for FD-DEC 033 ("no, but" answers). None is in the scored 60.
    "Does Apple's 2023 10-K discuss cryptocurrency as a risk?",                       # likely no, nothing related
    "Does Walmart's fiscal 2025 10-K discuss climate-related litigation as a risk?",  # no, but climate and litigation
    "What does Netflix's 2024 10-K say about the effect of its ad-supported plan on churn?",  # subject yes, aspect no
    "What was Ford's average transaction price for the F-150 in 2024, according to its 10-K?",  # specific fact: abstain
    "Does Coca-Cola's 2023 10-K say that weight-loss drugs have already reduced its sales?",    # no, but a related risk
    # Added for FD-DEC 038 (a second look before an absence answer). The first is a deliberate sibling of scored
    # QA21's failure (same company, other year, other wording); the second should find nothing more.
    "What does Netflix's 2024 10-K say about the effect of password sharing on membership growth?",
    "Does Apple's 2024 10-K say it depends on TSMC?",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    rec = Recorder(ROOT / "data" / "model-cache", offline="--offline" in sys.argv)
    cat = catalog(ROOT)
    out = []
    for q in DEV:
        t = ask(q, ROOT, cat, rec)
        out.append(t)
        r = t["result"]
        print(f"\n## {q}\n   stage={t['stage']} result={r['type']}")
        if r["type"] == "answer":
            print("   " + r["text"])
            for c in r["citations"]:
                print(f"     [{c['accession']} {c['section']} {c['start']}-{c['end']}] {c['quote'][:120]!r}")
        else:
            print("   abstain: " + r["reason"][:200])
        for p in t["problems"]:
            print("   PROBLEM " + p)
    d = ROOT / "data" / "qa"
    d.mkdir(parents=True, exist_ok=True)
    (d / "dev.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n" for t in out),
                                 encoding="utf-8")
    c = Counter((t["stage"], t["result"]["type"]) for t in out)
    print(f"\n{dict(c)} · recorded {rec.calls} new, replayed {rec.hits} · prompt {out[0]['prompt_version']}")


if __name__ == "__main__":
    main()
