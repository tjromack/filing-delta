"""The Fact type: an XBRL-tagged financial-statement value. Never narrative (FD-DEC 025).

A Fact is not text from a filing section. It never enters section text, the diff, or the QA index as a citable span,
and every rendering states where it came from and whether those statements are audited (10-K) or unaudited interim
statements (10-Q).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

PROVENANCE = {
    "10-K": "XBRL-tagged value from the 10-K's audited financial statements",
    "10-Q": "XBRL-tagged value from the 10-Q's unaudited interim financial statements",
}


def dec_str(d: Decimal | int | float | str) -> str:
    """One canonical spelling per number, so values from both sources compare as strings: plain digits, no exponent,
    no trailing zeros. 13380000000 -> '13380000000'; 2.970 -> '2.97'; -0 -> '0'. A float goes through str() first."""
    d = Decimal(str(d)) if not isinstance(d, Decimal) else d
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "0") else s


@dataclass(frozen=True)
class Fact:
    concept: str                  # "us-gaap:Revenues"
    value: str | None             # exact decimal as a string (None = xsi:nil)
    unit: str                     # "USD", "shares", "USD/shares", "pure"
    start: str | None             # None for an instant
    end: str
    dims: tuple = ()              # sorted ((dimension, member), ...); () = consolidated / no dimension
    decimals: str | None = None
    accession: str = ""
    source: str = ""              # "inline" | "companyfacts"

    def key(self) -> tuple:
        return (self.concept, self.unit, self.start, self.end, self.dims)

    def sort_key(self) -> tuple:
        return (self.concept, self.unit, self.start or "", self.end, self.dims)

    def to_json(self) -> dict:
        d = asdict(self)
        d["dims"] = [list(x) for x in self.dims]
        return d

    @classmethod
    def from_json(cls, d: dict) -> Fact:
        return cls(**{**d, "dims": tuple(tuple(x) for x in d.get("dims", []))})


def render(fact: Fact, form: str) -> str:
    """The only way a fact is shown: the value with its provenance. There is no bare-value rendering."""
    if form not in PROVENANCE:
        raise ValueError(f"no provenance wording for form {form!r}")
    period = f"{fact.start} to {fact.end}" if fact.start else f"as of {fact.end}"
    return f"{fact.concept} = {fact.value} {fact.unit} ({period}). {PROVENANCE[form]}, accession {fact.accession}."
