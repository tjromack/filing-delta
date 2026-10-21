"""Human-readable rendering of a change. Shared by the labeling sheets and the classifier prompt, so the labeler
and the model see a change in exactly the same form."""
from __future__ import annotations

from difflib import SequenceMatcher


def diff_segments(a: str, b: str, keep: int = 15) -> list[tuple[str, str]]:
    """The same word-level diff as typed segments: ("eq" | "del" | "ins" | "gap", text). For HTML rendering."""
    wa, wb = a.split(), b.split()
    out: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if tag == "equal":
            run = wa[i1:i2]
            if len(run) > 40:
                out += [("eq", " ".join(run[:keep])), ("gap", f"{len(run) - 2 * keep} unchanged words"),
                        ("eq", " ".join(run[-keep:]))]
            else:
                out.append(("eq", " ".join(run)))
        if tag in ("delete", "replace"):
            out.append(("del", " ".join(wa[i1:i2])))
        if tag in ("insert", "replace"):
            out.append(("ins", " ".join(wb[j1:j2])))
    return out


def inline_diff(a: str, b: str) -> str:
    """Word-level inline diff on the original words: [-deleted-] {+inserted+}.

    Long unchanged stretches are collapsed ("… 57 unchanged words …") so every change stays visible, however long
    the paragraph.
    """
    wa, wb = a.split(), b.split()
    out = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
        if tag == "equal":
            run = wa[i1:i2]
            if len(run) > 40:
                run = run[:15] + [f"… ({len(run) - 30} unchanged words) …"] + run[-15:]
            out.append(" ".join(run))
        if tag in ("delete", "replace"):
            out.append("[-" + " ".join(wa[i1:i2]) + "-]")
        if tag in ("insert", "replace"):
            out.append("{+" + " ".join(wb[j1:j2]) + "+}")
    return " ".join(out)
