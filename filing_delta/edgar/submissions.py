"""Filing lists from the EDGAR submissions API, plus pure corpus selection against corpus.toml."""
from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .client import EdgarClient

SUBMISSIONS = "https://data.sec.gov/submissions/"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data/"
_COLUMNS = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument", "isInlineXBRL")


@dataclass(frozen=True, order=True)
class Filing:
    cik: int
    form: str
    report_date: str
    filing_date: str
    accession: str
    primary_document: str
    is_ixbrl: bool
    company: str = ""

    @property
    def url(self) -> str:
        return f"{ARCHIVES}{self.cik}/{self.accession.replace('-', '')}/{self.primary_document}"


def submissions_url(cik: int) -> str:
    return f"{SUBMISSIONS}CIK{cik:010d}.json"


def _rows(block: dict, cik: int, company: str) -> list[Filing]:
    n = len(block["accessionNumber"])
    if any(len(block.get(c, [])) != n for c in _COLUMNS):
        raise ValueError(f"CIK {cik}: submissions columns have unequal lengths")
    return [
        Filing(cik=cik, form=block["form"][i], report_date=block["reportDate"][i] or "",
               filing_date=block["filingDate"][i], accession=block["accessionNumber"][i],
               primary_document=block["primaryDocument"][i], is_ixbrl=bool(block["isInlineXBRL"][i]),
               company=company)
        for i in range(n)
    ]


def all_filings(client: EdgarClient, cik: int, filed_since: str | None = None) -> list[Filing]:
    """Every filing for a CIK: the 'recent' block plus each paged history file it lists.

    History pages whose ``filingTo`` is before ``filed_since`` are not requested at all (fewer EDGAR requests).
    """
    head = json.loads(client.get(submissions_url(cik)).body)
    company = head.get("name", "")
    filings = _rows(head["filings"]["recent"], cik, company)
    for page in head["filings"].get("files", []):
        if filed_since and page.get("filingTo", "9999") < filed_since:
            continue
        filings += _rows(json.loads(client.get(SUBMISSIONS + page["name"]).body), cik, company)
    # Pages can overlap at their edges; de-duplicate on accession number.
    unique = {f.accession: f for f in filings}
    return sorted(unique.values())


@dataclass(frozen=True)
class CorpusSpec:
    ciks: tuple[int, ...]
    k_period_from: str
    k_period_to: str
    q_filed_from: str
    q_filed_to: str

    @property
    def earliest_filing_date(self) -> str:
        """No in-window filing can be filed before this (a report is filed after its period ends)."""
        return min(self.k_period_from, self.q_filed_from)

    @classmethod
    def load(cls, path: Path) -> CorpusSpec:
        d = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        k, q = d["windows"]["10-K"], d["windows"]["10-Q"]
        return cls(ciks=tuple(c["cik"] for c in d["company"]),
                   k_period_from=k["period_from"], k_period_to=k["period_to"],
                   q_filed_from=q["filed_from"], q_filed_to=q["filed_to"])


def select(filings: list[Filing], spec: CorpusSpec) -> list[Filing]:
    """Pure: the filings inside the corpus windows. Amendments are excluded by exact form match."""
    out = []
    for f in filings:
        if f.form == "10-K" and spec.k_period_from <= f.report_date <= spec.k_period_to:
            out.append(f)
        elif f.form == "10-Q" and spec.q_filed_from <= f.filing_date <= spec.q_filed_to:
            out.append(f)
    return sorted(out)
