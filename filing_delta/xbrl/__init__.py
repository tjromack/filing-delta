"""XBRL financial-statement facts (M5). Context beside the narrative sections, never part of them (FD-DEC 025)."""
from .companyfacts import companyfacts_url, facts_for
from .facts import Fact, dec_str, render
from .inline import InlineFacts, extract
from .periods import duration_class, headline, role

__all__ = ["Fact", "InlineFacts", "companyfacts_url", "dec_str", "duration_class", "extract", "facts_for",
           "headline", "render", "role"]
