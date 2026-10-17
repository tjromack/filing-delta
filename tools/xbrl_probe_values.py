"""M5 design probe (docs/design/xbrl-join.md §1): every dollar amount in MD&A vs. any USD XBRL fact (company-facts
API) reported in the same filing, matched by value alone at the stated precision. No model; offline after fetch.

    python tools/xbrl_probe_values.py
"""
import csv, json, os, re, sys, random
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.cli import load_env, CACHE_DIR
from filing_delta.edgar import EdgarClient

load_env()
man = list(csv.DictReader(open(ROOT / "corpus" / "manifest.csv", encoding="utf-8")))
SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
AMT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(thousand|million|billion|trillion)?", re.I)
missing = []
tot = Counter()
by_co = defaultdict(Counter)
examples = defaultdict(list)
with EdgarClient(os.environ.get("EDGAR_USER_AGENT"), CACHE_DIR, offline=True) as c:
    facts_by_cik = {}
    for r in man:
        cik = int(r["cik"])
        if cik not in facts_by_cik:
            d = json.loads(c.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json").body)
            by_acc = defaultdict(lambda: defaultdict(set))
            for tax, tags in d["facts"].items():
                for tag, t in tags.items():
                    for unit, rows in t["units"].items():
                        if unit != "USD":
                            continue
                        for f in rows:
                            by_acc[f["accn"]][f["val"]].add(tag)
            facts_by_cik[cik] = by_acc
        by_acc = facts_by_cik[cik]
        if r["accession"] not in by_acc:
            missing.append((r["company"], r["form"], r["report_date"], r["accession"]))
        sec = "10K_7" if r["form"] == "10-K" else "10Q_P1_2"
        p = ROOT / "data" / "sections" / r["accession"] / f"{sec}.txt"
        if not p.exists():
            tot["no section"] += 1
            continue
        text = p.read_text(encoding="utf-8")
        vals = by_acc.get(r["accession"], {})
        for m in AMT.finditer(text):
            num = float(m.group(1).replace(",", ""))
            sc = SCALE.get((m.group(2) or "").lower(), 1)
            tot["amounts"] += 1
            by_co[r["company"]]["amounts"] += 1
            if sc == 1 and num < 1000:
                tot["small/unscaled"] += 1
                continue
            v = num * sc
            dec = len(m.group(1).split(".")[1]) if "." in m.group(1) else 0
            tol = 0.5 * sc / (10 ** dec) if sc > 1 else 0.5
            hit = [tags for val, tags in vals.items() if abs(val - v) <= tol]
            if hit:
                tot["match"] += 1
                by_co[r["company"]]["match"] += 1
                if len(examples["m"]) < 400:
                    examples["m"].append((r["company"], text[max(0, m.start() - 90):m.end() + 30].replace("\n", " "), sorted(set().union(*hit))[:4]))
            else:
                tot["no match"] += 1
print("filings with no companyfacts rows:", missing)
print(dict(tot))
for co, cn in by_co.items():
    print(f"  {co[:24]:24} amounts={cn['amounts']:5} matched={cn['match']:5}")
random.seed(1)
for e in random.sample(examples["m"], 12):
    print("-", e[0][:12], "|", e[1], "|", e[2])
