#!/usr/bin/env python3
"""
Draw a stratified sample of programme stems for testing run_classifier.py.

Reads catalogue_scraper/data/.../index.csv and writes one stem per line to a
text file (default: test_set_<n>.txt), for use with run_classifier.py's
--test-set flag.

A random draw from the 470 programmes would be mostly Dornsife BAs and would
mostly miss the formats that break the parser: conservatory BMs, professional
BSWs, minors, architecture. So this stratifies across credential and school
and round-robins across strata (rather than sampling proportional to strata
size), so a rare credential like BArch or BSW (one programme each in the
whole corpus) still gets picked.

index.csv's `credential` column is blank for every minor (262 of 470 rows),
so credential is derived from the filename suffix instead, the same rule
run_classifier.program_name_from_stem uses.

Always force-includes the 3 largest files by content_character_count (these
are exactly the programmes with the big enumerated elective lists behind the
truncation problem) and the 15 stems in run_classifier.TEST_SET (so existing
review notes on those programmes stay comparable).

Usage
    python make_test_set.py --n 40
    python make_test_set.py --n 40 --out my_set.txt --seed 7
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from itertools import cycle, islice
from pathlib import Path

from run_classifier import DEGREE_WORDS, PROGRAMS_DIR, TEST_SET

HERE = Path(__file__).resolve().parent
INDEX_PATH = PROGRAMS_DIR.parent / "index.csv"


def credential_of(stem: str, program_name: str) -> str:
    """Same suffix rule as run_classifier.program_name_from_stem."""
    last = stem.split("_")[-1]
    if last in DEGREE_WORDS:
        return DEGREE_WORDS[last]
    if program_name.strip().lower().endswith("minor"):
        return "Minor"
    return "other"


def load_rows() -> list[dict]:
    with INDEX_PATH.open(newline="", encoding="utf-8") as fh:
        index_rows = list(csv.DictReader(fh))
    rows = []
    for r in index_rows:
        stem = r["output_filename"].rsplit(".", 1)[0]
        if not (PROGRAMS_DIR / f"{stem}.txt").exists():
            continue  # index.csv can list programmes the scrape didn't produce a file for
        rows.append(
            {
                "stem": stem,
                "school": r["school"],
                "chars": int(r["content_character_count"] or 0),
                "credential": credential_of(stem, r["program_name"]),
            }
        )
    return rows


def round_robin(iterables):
    """itertools recipe: round_robin('ABC', 'D', 'EF') --> A D E B F C."""
    iterators = [iter(it) for it in iterables]
    num_active = len(iterators)
    nexts = cycle(iter(it).__next__ for it in iterators)
    while num_active:
        try:
            for next_fn in nexts:
                yield next_fn()
        except StopIteration:
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))


def stratified_sample(rows: list[dict], n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    by_stem = {r["stem"]: r for r in rows}

    forced = {s for s in TEST_SET if s in by_stem}
    largest = sorted(rows, key=lambda r: r["chars"], reverse=True)[:3]
    forced |= {r["stem"] for r in largest}

    remaining = max(0, n - len(forced))
    pool = [r for r in rows if r["stem"] not in forced]

    by_credential: dict[str, list[dict]] = defaultdict(list)
    for r in pool:
        by_credential[r["credential"]].append(r)

    per_credential_order = []
    for cred in sorted(by_credential):
        by_school: dict[str, list[dict]] = defaultdict(list)
        for r in by_credential[cred]:
            by_school[r["school"]].append(r)
        school_buckets = list(by_school.values())
        for bucket in school_buckets:
            rng.shuffle(bucket)
        rng.shuffle(school_buckets)
        per_credential_order.append(list(round_robin(school_buckets)))

    rng.shuffle(per_credential_order)  # don't systematically favor one credential
    sampled = list(round_robin(per_credential_order))[:remaining]

    return sorted(forced) + [r["stem"] for r in sampled]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=40, help="sample size (default: 40)")
    ap.add_argument("--out", help="output file inside deg_requirement_parser (default: test_set_<n>.txt)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed, for a reproducible sample (default: 42)")
    args = ap.parse_args()

    if not INDEX_PATH.exists():
        print(f"missing: {INDEX_PATH}", file=sys.stderr)
        return 1

    rows = load_rows()
    by_stem = {r["stem"]: r for r in rows}
    stems = stratified_sample(rows, args.n, args.seed)

    out_path = HERE / (args.out or f"test_set_{args.n}.txt")
    out_path.write_text("\n".join(stems) + "\n", encoding="utf-8")

    creds = sorted({by_stem[s]["credential"] for s in stems if s in by_stem})
    print(f"Wrote {len(stems)} stems to {out_path}")
    print(f"Credentials covered ({len(creds)}): {', '.join(creds)}")
    if len(stems) != args.n:
        print(f"Note: wrote {len(stems)}, not {args.n} (the forced TEST_SET + 3-largest stems "
              "always go in, even if that's more than --n).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
