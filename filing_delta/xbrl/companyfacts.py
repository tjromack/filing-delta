"""Facts for one accession from the SEC company-facts API (M5 fallback source, FD-DEC 025). Pure.

The API keeps only facts without dimensions and reports each under the filing (`accn`) that tagged it. Rows from
other filings, amendments included, are dropped by accession.
"""
from __future__ import annotations

from .facts import Fact, dec_str


def companyfacts_url(cik: int) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def facts_for(doc: dict, accession: str) -> list[Fact]:
    out: dict[tuple, Fact] = {}
    for taxonomy, concepts in doc.get("facts", {}).items():
        for name, body in concepts.items():
            for unit, rows in body.get("units", {}).items():
                for r in rows:
                    if r.get("accn") != accession:
                        continue
                    f = Fact(concept=f"{taxonomy}:{name}", value=dec_str(r["val"]), unit=unit, start=r.get("start"),
                             end=r["end"], accession=accession, source="companyfacts")
                    out.setdefault(f.key(), f)
    return sorted(out.values(), key=Fact.sort_key)
