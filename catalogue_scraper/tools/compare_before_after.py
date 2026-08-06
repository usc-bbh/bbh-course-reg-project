#!/usr/bin/env python3
"""Before/after comparison of the baseline and corrected corpora.

Usage: compare_before_after.py BEFORE_AUDIT_CSV AFTER_AUDIT_CSV OUT_MD
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path


def load(p: Path) -> dict[str, dict]:
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    return {r["file_name"]: r for r in rows}


def stats(rows: list[dict]) -> dict:
    c = sorted(int(r["char_count"]) for r in rows if int(r["char_count"]) > 0)
    if not c:
        return {}
    return {
        "n": len(rows), "min": c[0], "max": c[-1],
        "mean": round(statistics.mean(c), 1), "median": statistics.median(c),
        "stdev": round(statistics.pstdev(c), 1) if len(c) > 1 else 0.0,
    }


def counts(rows: list[dict]) -> dict:
    return {
        "PASS": sum(1 for r in rows if r["validation_status"] == "PASS"),
        "REVIEW": sum(1 for r in rows if r["validation_status"] == "REVIEW"),
        "FAIL": sum(1 for r in rows if r["validation_status"] == "FAIL"),
        "html_contaminated": sum(1 for r in rows if r["critical_signatures"]),
        "no_title_heading": sum(1 for r in rows if r["body_has_title_heading"] == "False"),
        "zero_course_codes": sum(1 for r in rows if int(r["course_code_count"]) == 0),
        "title_mismatch": sum(1 for r in rows if r["title_mismatch"] == "True"),
        "duplicate_bodies": sum(1 for r in rows if int(r.get("duplicate_group_size") or 1) > 1),
    }


def main() -> int:
    before_p, after_p, out_p = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    before, after = load(before_p), load(after_p)
    b_rows, a_rows = list(before.values()), list(after.values())
    bc, ac = counts(b_rows), counts(a_rows)
    bs, as_ = stats(b_rows), stats(a_rows)

    L: list[str] = []
    A = L.append
    A("# Before / after comparison")
    A("")
    A("| Metric | Before (delivered) | After (corrected) | Change |")
    A("|---|---|---|---|")
    A(f"| Files produced | {len(b_rows)} | {len(a_rows)} | {len(a_rows) - len(b_rows):+d} |")
    for k in ("PASS", "REVIEW", "FAIL", "html_contaminated", "no_title_heading",
              "zero_course_codes", "title_mismatch", "duplicate_bodies"):
        A(f"| {k.replace('_', ' ')} | {bc[k]} | {ac[k]} | {ac[k] - bc[k]:+d} |")
    for k in ("min", "median", "mean", "max", "stdev"):
        A(f"| {k} chars | {bs.get(k)} | {as_.get(k)} | — |")
    A("")

    # missing / new files
    missing = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    A(f"- Files in baseline but not in corrected set: **{len(missing)}**"
      + (f" — {', '.join(missing[:12])}" if missing else ""))
    A(f"- Files in corrected set but not in baseline: **{len(added)}**"
      + (f" — {', '.join(added[:12])}" if added else ""))
    A("")

    # materially changed
    changed: list[tuple[str, dict, dict]] = []
    for name, a in after.items():
        b = before.get(name)
        if not b:
            continue
        if a["normalized_body_sha256"] != b["normalized_body_sha256"]:
            changed.append((name, b, a))
    A(f"## Materially changed files: {len(changed)}")
    A("")
    fixed = [(n, b, a) for n, b, a in changed
             if b["validation_status"] == "FAIL" and a["validation_status"] != "FAIL"]
    regressed = [(n, b, a) for n, b, a in changed
                 if b["validation_status"] != "FAIL" and a["validation_status"] == "FAIL"]
    other = [(n, b, a) for n, b, a in changed
             if (n, b, a) not in fixed and (n, b, a) not in regressed]
    A(f"- **Repaired** (FAIL → clean): {len(fixed)}")
    A(f"- **Regressed** (clean → FAIL): {len(regressed)}"
      + ("  ← investigate" if regressed else "  ✓ none"))
    A(f"- Other content changes (both clean; USC edits / renderer detail): {len(other)}")
    A("")
    if fixed:
        A("### Repaired files — reason each was corrected")
        A("")
        A("| file | before chars / codes | after chars / codes | reason it was wrong |")
        A("|---|---|---|---|")
        for n, b, a in sorted(fixed)[:200]:
            reason = (b["critical_signatures"] or b["failure_reasons"])[:70]
            A(f"| {n} | {b['char_count']} / {b['course_code_count']} | "
              f"{a['char_count']} / {a['course_code_count']} | {reason} |")
        A("")
    if regressed:
        A("### REGRESSIONS — must be investigated")
        A("")
        for n, b, a in regressed:
            A(f"- `{n}`: {a['failure_reasons']}")
        A("")
    if other:
        A("### Other changed files (sample)")
        A("")
        A("| file | before chars | after chars | before status | after status |")
        A("|---|---|---|---|---|")
        for n, b, a in sorted(other)[:40]:
            A(f"| {n} | {b['char_count']} | {a['char_count']} | "
              f"{b['validation_status']} | {a['validation_status']} |")
        A("")

    A("## Five smallest / largest, after correction")
    A("")
    nz = sorted((r for r in a_rows if int(r["char_count"]) > 0),
                key=lambda r: int(r["char_count"]))
    A("Smallest: " + ", ".join(
        f"{r['file_name']} ({r['char_count']}, {r['validation_status']})" for r in nz[:5]))
    A("")
    A("Largest: " + ", ".join(
        f"{r['file_name']} ({r['char_count']}, {r['validation_status']})" for r in nz[-5:][::-1]))
    out_p.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))
    print(f"\nwrote {out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
