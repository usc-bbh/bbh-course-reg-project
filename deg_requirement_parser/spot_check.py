#!/usr/bin/env python3
"""
Build a human review sheet from classifier output.

For each out/<stem>.json, lists every constraint with its source sentence next to
the family and details the model chose, plus a blank verdict column to fill in.
Low-confidence items and unclassified text are listed first, since that is where
errors usually are.

Usage
    python spot_check.py                      # every programme in out/
    python spot_check.py --only 025_astronomy_ba
    python spot_check.py --low-only           # only medium/low confidence items

Writes out/review_sheet.md. Mark each row OK / WRONG FAMILY / WRONG DETAILS, then
move each WRONG sentence into constraint_taxonomy.md as a new example.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "out"
CONF_ORDER = {"low": 0, "medium": 1, "high": 2}


def cell(text: str) -> str:
    """Make text safe inside a markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def review_programme(path: Path, low_only: bool) -> tuple[list[str], Counter]:
    data = json.loads(path.read_text(encoding="utf-8"))
    constraints = data.get("constraints") or []
    unclassified = data.get("unclassified") or []
    families = Counter(c.get("family", "?") for c in constraints)

    lines = [
        f"## {data.get('program', path.stem)}",
        "",
        f"Status: **{data.get('status', '?')}**. "
        f"{len(constraints)} constraints, {len(unclassified)} unclassified.  "
        + ", ".join(f"{fam}: {n}" for fam, n in families.most_common()),
        "",
    ]

    if unclassified:
        lines += ["**Unclassified text** (should any of these have been a constraint?)", ""]
        lines += [f"- {cell(u if isinstance(u, str) else json.dumps(u))}" for u in unclassified]
        lines.append("")

    rows = sorted(constraints, key=lambda c: CONF_ORDER.get(c.get("confidence"), -1))
    if low_only:
        rows = [c for c in rows if c.get("confidence") != "high"]

    if rows:
        lines += [
            "| id | conf | source sentence | family | details | verdict |",
            "|---|---|---|---|---|---|",
        ]
        for c in rows:
            lines.append(
                f"| {cell(c.get('id', ''))} | {cell(c.get('confidence', ''))} "
                f"| {cell(c.get('source_text', ''))} | {cell(c.get('family', ''))} "
                f"| `{cell(json.dumps(c.get('details', {})))}` |  |"
            )
        lines.append("")
    return lines, families


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="specific stems")
    ap.add_argument("--low-only", action="store_true", help="skip high-confidence items")
    ap.add_argument("--out-dir", default="out", help="output folder to read (default: out)")
    args = ap.parse_args()
    OUT_DIR = HERE / args.out_dir

    files = sorted(p for p in OUT_DIR.glob("*.json"))
    if args.only:
        files = [p for p in files if p.stem in set(args.only)]
    if not files:
        raise SystemExit(f"No output JSON found in {OUT_DIR}. Run run_classifier.py first.")

    body, totals = [], Counter()
    for path in files:
        try:
            lines, fams = review_programme(path, args.low_only)
        except json.JSONDecodeError as exc:
            lines, fams = [f"## {path.stem}", "", f"Invalid JSON: {exc}", ""], Counter()
        body += lines
        totals += fams

    header = [
        "# Classifier review sheet",
        "",
        f"{len(files)} programmes. Family totals: "
        + ", ".join(f"{fam}: {n}" for fam, n in totals.most_common()),
        "",
        "Verdicts: OK / WRONG FAMILY / WRONG DETAILS. "
        "A high Manual Review share means the taxonomy needs more examples.",
        "",
    ]
    sheet = OUT_DIR / "review_sheet.md"
    sheet.write_text("\n".join(header + body), encoding="utf-8")
    print(f"Wrote {sheet} ({len(files)} programmes)")


if __name__ == "__main__":
    main()
