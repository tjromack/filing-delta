"""M5 design probe (docs/design/xbrl-join.md §1): inline XBRL facts read from a cached primary document (no network).

    python tools/xbrl_probe_inline.py <accession> [...]
"""
import csv, os, sys
from collections import Counter
from pathlib import Path
from lxml import etree
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.cli import load_env, CACHE_DIR
from filing_delta.edgar import EdgarClient

load_env()
man = [r for r in csv.DictReader(open(ROOT / "corpus" / "manifest.csv", encoding="utf-8")) if r["is_ixbrl"] == "1"]
pick = [r for r in man if r["accession"] in sys.argv[1:]] or man[:1]
IX = "http://www.xbrl.org/2013/inlineXBRL"
with EdgarClient(os.environ.get("EDGAR_USER_AGENT"), CACHE_DIR, offline=True) as c:
    for r in pick:
        body = c.get(r["url"]).body
        root = etree.fromstring(body, etree.XMLParser(huge_tree=True, recover=True))
        ns = {"ix": IX, "xbrli": "http://www.xbrl.org/2003/instance", "xbrldi": "http://xbrl.org/2006/xbrldi"}
        ctx = {}
        for cx in root.iterfind(".//xbrli:context", ns):
            dims = [(m.get("dimension"), (m.text or "").strip()) for m in cx.iterfind(".//xbrldi:explicitMember", ns)]
            per = cx.find("xbrli:period", ns)
            inst = per.findtext("xbrli:instant", namespaces=ns)
            span = (per.findtext("xbrli:startDate", namespaces=ns), per.findtext("xbrli:endDate", namespaces=ns))
            ctx[cx.get("id")] = (inst or span, dims)
        facts = root.findall(".//ix:nonFraction", ns)
        dimd = sum(1 for f in facts if ctx.get(f.get("contextRef"), (None, []))[1])
        names = Counter(f.get("name") for f in facts)
        print(r["company"], r["form"], r["report_date"], "contexts", len(ctx), "nonFraction", len(facts), "dimensional", dimd)
        rev = [f for f in facts if f.get("name") in ("us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")]
        for f in rev[:8]:
            per, dims = ctx[f.get("contextRef")]
            print("   ", f.get("name").split(":")[1][:20], "".join(f.itertext()).strip(), "scale", f.get("scale"),
                  "sign", f.get("sign"), per, [d[1].split(":")[-1] for d in dims])
