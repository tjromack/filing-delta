"""Repository hygiene: no control characters in tracked text files.

During M2, patching regex source through a shell heredoc turned `\\b` into a literal backspace (0x08) three times.
The regexes silently stopped matching. This catches it.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".py", ".md", ".toml", ".json", ".csv", ".txt", ".yml", ".yaml"}


def test_no_control_characters_in_tracked_text_files():
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split()
    bad = {}
    for f in files:
        path = ROOT / f
        if path.suffix in TEXT and path.is_file():
            text = path.read_text(encoding="utf-8")
            hits = sorted({hex(ord(c)) for c in text if ord(c) < 32 and c not in "\n\t\r"})
            if hits:
                bad[f] = hits
    assert not bad, bad
