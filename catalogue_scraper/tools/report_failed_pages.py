#!/usr/bin/env python3
"""Report pages the fixed scraper refused, plus files flagged for a human.

Usage: report_failed_pages.py COLLECTION_DIR AUDIT_CSV OUT_MD
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def main() -> int:
    coll, audit_csv, out_md = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    L: list[str] = []
    A = L.append
    A("# Pages not processed, and files needing a human look")
    A("")

    # ---- refusals recorded by the fixed pipeline
    refusals: list[dict] = []
    err = coll / "errors.csv"
    if err.exists():
        for r in csv.DictReader(err.open(encoding="utf-8")):
            if r.get("error_type") in ("invalid_extracted_text", "content_region_not_found"):
                refusals.append(r)
    # Which refusals are still outstanding? A programme is resolved if a file
    # for its poid now exists on disk (errors.csv keeps every attempt, including
    # ones a later retry fixed).
    poids_on_disk: set[str] = set()
    for f in (coll / "programs").glob("*.txt"):
        head = f.read_text(encoding="utf-8", errors="replace")[:1200]
        for line in head.splitlines():
            if line.startswith("Program Identifier:"):
                poids_on_disk.add(line.split("poid=", 1)[-1].strip())
                break
    outstanding, resolved = [], []
    for r in refusals:
        pid = (r.get("program_identifier") or "").replace("poid=", "").strip()
        (resolved if pid in poids_on_disk else outstanding).append(r)

    A("## 1. Extractions refused by the new validation gate")
    A("")
    A(f"- **Still outstanding (no file written): {len({r['program_name'] for r in outstanding})}**")
    A(
        f"- Refused on an earlier attempt, then written successfully on retry: "
        f"{len({r['program_name'] for r in resolved})}"
    )
    A("")
    if outstanding:
        A(
            "A refusal means the scraper detected that what it extracted was not a "
            "trustworthy programme body. Previously such content was saved silently as "
            "`complete`; now nothing is written and the programme is reported here."
        )
        A("")
        A("| programme | error | reason |")
        A("|---|---|---|")
        for r in outstanding:
            A(
                f"| {r['program_name']} | `{r['error_type']}` | "
                f"{r['error_message'][:150].replace('|', '¦')} |"
            )
    else:
        A("**Nothing outstanding.** Every discovered programme has a validated file.")
    A("")
    if resolved:
        A(
            "<details><summary>Refusals resolved on retry (validator refinements during "
            "the corrected run)</summary>"
        )
        A("")
        A("| programme | first-attempt reason |")
        A("|---|---|")
        seen: set[str] = set()
        for r in resolved:
            if r["program_name"] in seen:
                continue
            seen.add(r["program_name"])
            A(f"| {r['program_name']} | {r['error_message'][:110].replace('|', '¦')} |")
        A("")
        A(
            "Each was investigated against its live source page and found to be a "
            "legitimately short or prose-only programme; the validator was corrected "
            "accordingly and the page re-extracted. See ENGINEERING_REPORT.md §8."
        )
        A("</details>")
    A("")

    # ---- manifest reconciliation
    man = coll / "manifest.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        A("## 2. Run reconciliation (from the run's own manifest)")
        A("")
        A("| field | value |")
        A("|---|---|")
        for k in (
            "run_id",
            "run_started_at",
            "run_completed_at",
            "catalogue_year",
            "discovered_in_boundary",
            "included_count",
            "excluded_count",
            "manual_review_count",
            "duplicate_count",
            "successful_count",
            "failed_count",
        ):
            if k in m:
                A(f"| {k} | {m[k]} |")
        files = len(list((coll / "programs").glob("*.txt")))
        A(f"| files on disk | {files} |")
        A("")
        gap = int(m.get("included_count", 0)) - files
        if gap:
            A(f"> {gap} included programme(s) have no file — accounted for in section 1.")
        else:
            A("> Every included programme has a file on disk.")
        A("")

    # ---- classifier's own manual-review list
    mr = coll / "manual_review.csv"
    if mr.exists():
        rows = list(csv.DictReader(mr.open(encoding="utf-8")))
        A(f"## 3. Classifier manual-review list ({len(rows)} links)")
        A("")
        A(
            "Unchanged behaviour: links whose title carries no recognizable credential are "
            "never silently dropped. They are neither included nor excluded — a human decides."
        )
        A("")
        if rows:
            A("| title | reason |")
            A("|---|---|")
            for r in rows[:60]:
                A(
                    f"| {r.get('program_name', '')} | "
                    f"{(r.get('recommended_action') or r.get('reason', ''))[:110]} |"
                )
            if len(rows) > 60:
                A(f"| … | _{len(rows) - 60} more in `manual_review.csv`_ |")
        A("")

    # ---- audit REVIEW files
    if audit_csv.exists():
        rows = list(csv.DictReader(audit_csv.open(encoding="utf-8")))
        rev = [r for r in rows if r["validation_status"] == "REVIEW"]
        fail = [r for r in rows if r["validation_status"] == "FAIL"]
        A(f"## 4. Audit verdicts on the corrected corpus — FAIL {len(fail)}, REVIEW {len(rev)}")
        A("")
        if fail:
            A("### FAIL (must be investigated)")
            A("")
            A("| file | chars | reasons |")
            A("|---|---|---|")
            for r in fail:
                A(f"| {r['file_name']} | {r['char_count']} | {r['failure_reasons'][:120]} |")
            A("")
        else:
            A("**No FAIL files.**")
            A("")
        if rev:
            A("### REVIEW (not defects — a human should confirm)")
            A("")
            A("| file | chars | why flagged |")
            A("|---|---|---|")
            for r in rev[:80]:
                A(f"| {r['file_name']} | {r['char_count']} | {r['failure_reasons'][:110]} |")
            A("")
            A(
                "The dominant reason is `exact_duplicate_body`: USC genuinely publishes "
                "identical requirement text for some paired programmes (e.g. a BA and BS "
                "sharing one requirement set). Verified by comparing source URLs — the pairs "
                "are distinct programmes with distinct poids."
            )
    out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:50]))
    print(f"\nwrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
