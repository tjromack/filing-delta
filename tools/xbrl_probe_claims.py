"""M5 design probe (docs/design/xbrl-join.md §1): headline-metric claims in MD&A ("net income was $X"), matched by
concept to same-filing, non-dimensional company-facts values. No model; offline after fetch.

    python tools/xbrl_probe_claims.py
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
LEX = [  # phrase -> concepts
    (r"(?:total )?net revenues?|total revenues?|net sales|total net sales|revenues?", ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"]),
    (r"net (?:income|earnings)(?: attributable to [\w .,&]{3,40}?)?", ["NetIncomeLoss", "ProfitLoss"]),
    (r"operating income", ["OperatingIncomeLoss"]),
    (r"(?:cash (?:provided by|from|flows? from) operating activities|operating cash flows?)", ["NetCashProvidedByUsedInOperatingActivities"]),
]
NONGAAP = re.compile(r"adjusted|organic|excluding|non-gaap|comparable|core|underlying|managed basis|constant currency|pro forma", re.I)
SCALE = {"thousand": 1e3, "million": 1e6, "billion": 1e9}
AMT = r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(thousand|million|billion)?"
pats = [(re.compile(rf"\b({p})\b[^.$;]{{0,50}}?(?:was|were|of|totaled|increased[^.$;]{{0,25}}to|decreased[^.$;]{{0,25}}to|grew[^.$;]{{0,25}}to)\s+{AMT}", re.I), cs) for p, cs in LEX]
res = Counter(); ex = defaultdict(list)
with EdgarClient(os.environ.get("EDGAR_USER_AGENT"), CACHE_DIR, offline=True) as c:
    cf = {}
    for r in man:
        cik = int(r["cik"])
        if cik not in cf:
            d = json.loads(c.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json").body)
            idx = defaultdict(list)
            for tag, t in d["facts"].get("us-gaap", {}).items():
                for f in t["units"].get("USD", []):
                    idx[(f["accn"], tag)].append(f)
            cf[cik] = idx
        sec = "10K_7" if r["form"] == "10-K" else "10Q_P1_2"
        p = ROOT / "data" / "sections" / r["accession"] / f"{sec}.txt"
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        for pat, concepts in pats:
            for m in pat.finditer(text):
                res["claims"] += 1
                window = text[max(0, m.start() - 120):m.start()] + m.group(0)
                if NONGAAP.search(window):
                    res["non-GAAP wording"] += 1
                    continue
                num = float(m.group(2).replace(",", "")); sc = SCALE.get((m.group(3) or "").lower(), 1)
                dec = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
                v, tol = num * sc, 0.5 * sc / 10 ** dec
                cands = [f for cpt in concepts for f in cf[cik].get((r["accession"], cpt), [])]
                if not cands:
                    res["no fact for concept"] += 1; continue
                hit = [f for f in cands if abs(f["val"] - v) <= tol]
                k = "value matches a fact of that concept" if hit else "no matching value (segment/other period/differs)"
                res[k] += 1
                ex[k].append((r["company"][:14], text[max(0, m.start() - 60):m.end() + 10].replace("\n", " ")))
print(dict(res))
random.seed(3)
for k in ex:
    print("\n##", k)
    for e in random.sample(ex[k], min(8, len(ex[k]))):
        print("-", e[0], "|", e[1])
