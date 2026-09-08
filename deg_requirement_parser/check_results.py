#!/usr/bin/env python3
"""
Validate classifier output and write a summary CSV.

Checks each out/<stem>.json for:
  - valid JSON with the top-level fields the prompt specifies
  - every constraint carrying id, family, source_text, description, details
  - every `family` value existing in constraint_taxonomy.md (no invented families)
  - confidence being high / medium / low
  - source_text appearing verbatim in the scraped programme file

Usage
    python check_results.py
    python check_results.py --verbose     # list every problem, not just counts

Exits non-zero if anything failed, so it is usable as a gate.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PROGRAMS_DIR = (
    REPO
    / "catalogue_scraper"
    / "data"
    / "usc_undergrad_complete_catalogue_2026_2027"
    / "programs"
)
TAXONOMY_PATH = HERE / "constraint_taxonomy.md"
OUT_DIR = HERE / "out"

REQUIRED_TOP = ["program", "status", "constraints", "unclassified"]
REQUIRED_CONSTRAINT = ["id", "family", "source_text", "description", "details"]
VALID_STATUS = {"ok", "partial", "failed"}
VALID_CONFIDENCE = {"high", "medium", "low"}


def taxonomy_families(path: Path) -> set[str]:
    """Family names are declared in the taxonomy as: `family`: `"Course Selection"`."""
    text = path.read_text(encoding="utf-8")
    names = set(re.findall(r'`family`:\s*`"([^"]+)"`', text))
    if not names:  # fall back to the JSON examples
        names = set(re.findall(r'"family":\s*"([^"]+)"', text))
    return names


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def check_file(path: Path, families: set[str], sources: dict[str, str]) -> tuple[dict, list[str]]:
    problems: list[str] = []
    stem = path.stem
    row = {
        "file": stem,
        "status": "",
        "constraints": 0,
        "unclassified": 0,
        "problems": 0,
        "verbatim_misses": 0,
        "low_confidence": 0,
    }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"{stem}: invalid JSON ({exc})")
        row["problems"] = 1
        return row, problems

    for field in REQUIRED_TOP:
        if field not in data:
            problems.append(f"{stem}: missing top-level field '{field}'")

    status = data.get("status", "")
    row["status"] = status
    if status and status not in VALID_STATUS:
        problems.append(f"{stem}: status '{status}' not in {sorted(VALID_STATUS)}")

    constraints = data.get("constraints") or []
    unclassified = data.get("unclassified") or []
    row["constraints"] = len(constraints)
    row["unclassified"] = len(unclassified)

    if status == "ok" and unclassified:
        problems.append(f"{stem}: status is 'ok' but there are {len(unclassified)} unclassified entries")
    if status == "partial" and not unclassified:
        problems.append(f"{stem}: status is 'partial' but nothing is unclassified")

    source_text = sources.get(stem)
    seen_ids = set()

    for idx, c in enumerate(constraints):
        label = f"{stem}[{idx}]"
        if not isinstance(c, dict):
            problems.append(f"{label}: not an object")
            continue

        for field in REQUIRED_CONSTRAINT:
            if field not in c:
                problems.append(f"{label}: missing '{field}'")

        cid = c.get("id")
        if cid in seen_ids:
            problems.append(f"{label}: duplicate id '{cid}'")
        seen_ids.add(cid)

        fam = c.get("family")
        if fam and fam not in families:
            problems.append(f"{label}: family '{fam}' is not in the taxonomy")

        conf = c.get("confidence")
        if conf is not None and conf not in VALID_CONFIDENCE:
            problems.append(f"{label}: confidence '{conf}' not in {sorted(VALID_CONFIDENCE)}")
        if conf == "low":
            row["low_confidence"] += 1

        if not isinstance(c.get("details"), dict):
            problems.append(f"{label}: details is not an object")

        st = c.get("source_text") or ""
        if source_text is not None and st and norm(st) not in norm(source_text):
            row["verbatim_misses"] += 1
            problems.append(f"{label}: source_text not found verbatim in the programme file")

    for idx, u in enumerate(unclassified):
        if not isinstance(u, dict) or "source_text" not in u:
            problems.append(f"{stem}.unclassified[{idx}]: missing source_text")

    row["problems"] = len(problems)
    return row, problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true", help="print every problem")
    args = ap.parse_args()

    if not TAXONOMY_PATH.exists():
        print(f"missing {TAXONOMY_PATH}", file=sys.stderr)
        return 1
    families = taxonomy_families(TAXONOMY_PATH)
    if not families:
        print("Could not find any family names in the taxonomy.", file=sys.stderr)
        return 1
    print(f"Taxonomy families ({len(families)}): {', '.join(sorted(families))}\n")

    outputs = sorted(p for p in OUT_DIR.glob("*.json") if p.name != "summary.json")
    if not outputs:
        print(f"No .json files in {OUT_DIR}. Run run_classifier.py first.")
        return 1

    sources: dict[str, str] = {}
    for p in outputs:
        src = PROGRAMS_DIR / f"{p.stem}.txt"
        if src.exists():
            sources[p.stem] = src.read_text(encoding="utf-8")

    rows, all_problems = [], []
    family_counts: Counter[str] = Counter()

    for p in outputs:
        row, problems = check_file(p, families, sources)
        rows.append(row)
        all_problems.extend(problems)
        try:
            for c in json.loads(p.read_text(encoding="utf-8")).get("constraints", []):
                if isinstance(c, dict) and c.get("family"):
                    family_counts[c["family"]] += 1
        except Exception:  # noqa: BLE001
            pass

    summary = OUT_DIR / "summary.csv"
    with summary.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"{'file':<56} {'status':<8} {'con':>4} {'unc':>4} {'prob':>5}")
    for r in rows:
        print(f"{r['file']:<56} {r['status']:<8} {r['constraints']:>4} {r['unclassified']:>4} {r['problems']:>5}")

    print("\nConstraints by family:")
    for fam, n in family_counts.most_common():
        print(f"  {n:>4}  {fam}")
    unused = sorted(families - set(family_counts))
    if unused:
        print(f"\nFamilies never used: {', '.join(unused)}")
        print("Not necessarily wrong on a 15-file sample, but worth a look.")

    if all_problems:
        print(f"\n{len(all_problems)} problem(s) found.")
        shown = all_problems if args.verbose else all_problems[:20]
        for p in shown:
            print(f"  - {p}")
        if len(all_problems) > len(shown):
            print(f"  ... and {len(all_problems) - len(shown)} more (use --verbose)")
    else:
        print("\nNo problems found.")

    print(f"\nSummary written to {summary}")
    return 1 if all_problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
