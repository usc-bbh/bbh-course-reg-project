#!/usr/bin/env python3
"""
Summarize a run_classifier.py run from its run_log.csv. Reads only the log,
no ANTHROPIC_API_KEY or network access needed.

Prints:
  - total cost and total call time (sum of each programme's `seconds`; under
    concurrency this is more than the run's actual wall-clock duration)
  - the slowest programmes, with their out_tokens (is a slow call also a big one?)
  - every programme that hit stop_reason == max_tokens
  - the correlation between out_tokens and seconds (does output length drive
    latency, more than input size does?)
  - the correlation between chars_in and out_tokens (does a bigger programme
    file produce a bigger response, e.g. because of enumerated elective lists?)

Usage
    python analyze_run.py --out-dir out_sonnet5_40
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUMERIC_FIELDS = ("in_tokens", "out_tokens", "cost_usd", "seconds", "retries",
                   "chars_in", "cache_read_input_tokens")


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for key in NUMERIC_FIELDS:
            if r.get(key) not in (None, ""):
                r[key] = float(r[key])
    return rows


def read_meta(path: Path) -> dict | None:
    """run_meta.csv is a single row written by run_classifier.py; absent on older runs."""
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as fh:
        return next(iter(csv.DictReader(fh)), None)


def safe_correlation(pairs: list[tuple[float, float]]) -> float | None:
    """None if there isn't enough varying data for a correlation to mean anything."""
    if len(pairs) < 2:
        return None
    xs, ys = zip(*pairs)
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return statistics.correlation(xs, ys)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default="out", help="output folder to read (default: out)")
    ap.add_argument("--top", type=int, default=10, help="how many slowest programmes to list (default: 10)")
    args = ap.parse_args()

    log_path = HERE / args.out_dir / "run_log.csv"
    if not log_path.exists():
        print(f"missing: {log_path}. Run run_classifier.py first.", file=sys.stderr)
        return 1

    rows = load_rows(log_path)
    if not rows:
        print(f"{log_path} has no rows.")
        return 1

    total_seconds = sum(r.get("seconds", 0.0) or 0.0 for r in rows)
    total_cost = sum(r.get("cost_usd", 0.0) or 0.0 for r in rows)
    print(f"{len(rows)} programme(s) logged from {log_path}")
    print(f"Total cost: ${total_cost:.2f}")
    print(f"Total call time: {total_seconds:.1f}s (sum of per-call seconds)")

    meta = read_meta(log_path.parent / "run_meta.csv")
    if meta:
        wall = float(meta.get("wall_seconds") or 0.0)
        print(f"Run wall time: {wall:.1f}s, at --concurrency {meta.get('concurrency', '?')}"
              + (f" ({total_seconds / wall:.1f}x speedup)" if wall > 0 and total_seconds > wall * 1.05 else ""))
        print(f"Run started {meta.get('started_at', '?')}, finished {meta.get('finished_at', '?')}")
    else:
        print("Run wall time: n/a (no run_meta.csv — this log pre-dates whole-run timing)")

    print(f"\n{args.top} slowest programme(s):")
    slowest = sorted(rows, key=lambda r: r.get("seconds", 0.0) or 0.0, reverse=True)[: args.top]
    for r in slowest:
        seconds = r.get("seconds", 0.0) or 0.0
        out_tokens = int(r.get("out_tokens", 0) or 0)
        print(f"  {seconds:>6.1f}s  {out_tokens:>7,} out_tokens  {r['stem']}")

    truncated = [r for r in rows if r.get("stop_reason") == "max_tokens"]
    print(f"\n{len(truncated)} programme(s) hit stop_reason=max_tokens:")
    for r in truncated:
        out_tokens = int(r.get("out_tokens", 0) or 0)
        retries = int(r.get("retries", 0) or 0)
        print(f"  {r['stem']}  ({out_tokens:,} out_tokens, retries={retries})")

    out_seconds_pairs = [
        (r["out_tokens"], r["seconds"]) for r in rows
        if isinstance(r.get("out_tokens"), float) and isinstance(r.get("seconds"), float)
    ]
    chars_out_pairs = [
        (r["chars_in"], r["out_tokens"]) for r in rows
        if isinstance(r.get("chars_in"), float) and isinstance(r.get("out_tokens"), float)
    ]

    def report(label: str, pairs: list[tuple[float, float]]) -> None:
        corr = safe_correlation(pairs)
        if corr is None:
            print(f"\n{label}: n/a (need `seconds`/`chars_in` in this log, and more than one data point)")
        else:
            print(f"\n{label}: {corr:.3f}")

    report("Correlation(out_tokens, seconds)", out_seconds_pairs)
    report("Correlation(chars_in, out_tokens)", chars_out_pairs)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
