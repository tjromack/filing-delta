"""Download the data release named in release/manifest.json, verify it, and unpack it into data/ (M8).

    python tools/fetch_release.py      # needs the GitHub CLI (gh) logged in, or GH_TOKEN set (as in the Action)

Verifies the archive's sha256 against the committed manifest before unpacking, refuses any archive member that
would land outside data/, then checks each directory's digest. Skips the download when the archive is already in
dist/ and matches.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_release import MANIFEST, sha256_file, tree_digest  # noqa: E402


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    archive = ROOT / "dist" / m["asset"]
    if not (archive.exists() and sha256_file(archive) == m["sha256"]):
        archive.parent.mkdir(exist_ok=True)
        subprocess.run(["gh", "release", "download", m["tag"], "--pattern", m["asset"], "--dir", str(archive.parent),
                        "--clobber"], check=True, cwd=ROOT)
        if sha256_file(archive) != m["sha256"]:
            raise SystemExit(f"{m['asset']}: sha256 doesn't match release/manifest.json; refusing to unpack.")
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            target = (ROOT / member.name).resolve()
            if not (member.isfile() or member.isdir()) or not str(target).startswith(str((ROOT / "data").resolve())):
                raise SystemExit(f"refusing archive member {member.name!r}")
        if hasattr(tarfile, "data_filter"):
            tar.extractall(ROOT, filter="data")     # also blocks links, devices and absolute paths
        else:
            tar.extractall(ROOT)
    for rel, want in m["contents"].items():
        got, n = tree_digest(rel)
        if got != want["digest"]:
            raise SystemExit(f"{rel}: contents don't match the manifest ({n} files vs {want['files']}).")
    print(f"data release {m['tag']} verified and unpacked ({m['bytes'] / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
