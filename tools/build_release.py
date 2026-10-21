"""Package the data a clean clone needs into one archive, and record what it must contain (M8, FD-DEC 036).

    python tools/build_release.py      # -> dist/filing-delta-data-<date>.tar.gz + release/manifest.json

The archive holds the EDGAR response cache, the model-response cache and the timed-run latencies; everything else
in data/ regenerates from these. release/manifest.json (committed) records the archive's sha256 and a digest of each
directory's contents (sorted relative path + sha256 per file), so tools/fetch_release.py can verify the download and
tools/reproduce.py can verify what's on disk. Contains no .env, keys or User-Agent: see docs/design/m8.md §1.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENTS = ["data/edgar-cache", "data/model-cache", "data/qa/latency.jsonl"]
MANIFEST = ROOT / "release" / "manifest.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_of(rel: str) -> list[Path]:
    p = ROOT / rel
    if p.is_file():
        return [p]
    return sorted((f for f in p.rglob("*") if f.is_file() and f.suffix != ".part"), key=lambda f: f.as_posix())


def tree_digest(rel: str) -> tuple[str, int]:
    """One digest per entry: sha256 over 'relative/posix/path<TAB>sha256\\n' for every file, in sorted order."""
    h, n = hashlib.sha256(), 0
    for f in files_of(rel):
        h.update(f"{f.relative_to(ROOT).as_posix()}\t{sha256_file(f)}\n".encode())
        n += 1
    return h.hexdigest(), n


def main() -> None:
    date = time.strftime("%Y-%m-%d")
    name = f"filing-delta-data-{date}.tar.gz"
    out = ROOT / "dist" / name
    out.parent.mkdir(exist_ok=True)
    with tarfile.open(out, "w:gz", compresslevel=6) as tar:
        for rel in CONTENTS:
            for f in files_of(rel):
                ti = tar.gettarinfo(str(f), arcname=f.relative_to(ROOT).as_posix())
                ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = 0, 0, 0, "", ""
                with f.open("rb") as fh:
                    tar.addfile(ti, fh)
    trees = {}
    for rel in CONTENTS:
        d, n = tree_digest(rel)
        trees[rel] = {"digest": d, "files": n}
    manifest = {"tag": f"data-{date}", "asset": name, "sha256": sha256_file(out), "bytes": out.stat().st_size,
                "contents": trees}
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{out.relative_to(ROOT)}: {out.stat().st_size / 1e6:.0f} MB; "
          + ", ".join(f"{k} {v['files']} files" for k, v in trees.items()))


if __name__ == "__main__":
    sys.exit(main())
