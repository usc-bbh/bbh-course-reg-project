#!/usr/bin/env python3
"""Repeatability check: same source pages must yield the same substantive text.

Compares the normalized body hash of every file present in two collection
folders (e.g. the full corrected run and a second re-run of a subset), and
reports any file whose substantive content differs.

The comparison deliberately ignores the metadata header, because
`Retrieved At` and `Acquisition Mode` legitimately change between runs.

Usage: check_repeatability.py RUN_A_PROGRAMS_DIR RUN_B_PROGRAMS_DIR [OUT_MD]
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

MARKER = "OFFICIAL CATALOGUE CONTENT"


def body_hash(path: Path) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    body = text.split(MARKER, 1)[1] if MARKER in text else text
    norm = re.sub(r"\s+", " ", body).strip()
    return hashlib.sha256(norm.encode()).hexdigest(), len(norm)


def main() -> int:
    a_dir, b_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    a = {p.name: body_hash(p) for p in a_dir.glob("*.txt")}
    b = {p.name: body_hash(p) for p in b_dir.glob("*.txt")}
    common = sorted(set(a) & set(b))
    same = [n for n in common if a[n][0] == b[n][0]]
    diff = [n for n in common if a[n][0] != b[n][0]]

    L = [
        "# Repeatability check",
        "",
        f"- Run A: `{a_dir}` ({len(a)} files)",
        f"- Run B: `{b_dir}` ({len(b)} files)",
        f"- Files compared (present in both): **{len(common)}**",
        f"- **Byte-identical substantive content: {len(same)}/{len(common)}**",
        f"- Differing: {len(diff)}",
        "",
    ]
    if diff:
        L += ["## Differences", "", "| file | run A chars | run B chars |", "|---|---|---|"]
        L += [f"| {n} | {a[n][1]} | {b[n][1]} |" for n in diff]
    else:
        L.append("No differences. Extraction is deterministic for unchanged source pages.")
    L += [
        "",
        "Files only in A: " + (", ".join(sorted(set(a) - set(b))[:20]) or "none"),
        "",
        "Files only in B: " + (", ".join(sorted(set(b) - set(a))[:20]) or "none"),
    ]
    text = "\n".join(L) + "\n"
    print(text)
    if out:
        out.write_text(text, encoding="utf-8")
    return 0 if not diff else 1


if __name__ == "__main__":
    raise SystemExit(main())
