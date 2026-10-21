"""Load the filing catalog, refusing an empty one.

Kept outside the frozen pipeline files (version.FILES) so the check doesn't change the pipeline version. Found by
the M10 demo rehearsal: with no data/facts the catalog came back empty, every question was scoped out of the corpus,
and run_qa wrote a wrong report without complaint.
"""
from __future__ import annotations

from pathlib import Path

from .index import Filing, catalog


def load_catalog(root: Path) -> list[Filing]:
    cat = catalog(root)
    if not cat:
        raise FileNotFoundError("data/facts/ is empty: run `filing-delta facts` before anything that asks questions")
    return cat
