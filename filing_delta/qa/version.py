"""The QA pipeline's version: one hash over every file that decides an answer (scope, index, prompt, ask, verify).

Frozen in tests/golden/qa_pipeline.json before the labeled set is run (like the M4 prompt and the M5 matcher).
Line endings are normalized, so a Windows checkout and a Linux runner agree.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

FILES = ("answer.py", "ask.py", "index.py", "prompt.py", "scope.py")


def pipeline_version() -> str:
    here = Path(__file__).parent
    h = hashlib.sha256()
    for name in FILES:
        h.update(name.encode() + b"\0" + (here / name).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]
