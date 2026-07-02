#!/usr/bin/env python3
"""
redact_stars.py — Bulletproof, structure-faithful redaction for USC STARS
Degree Progress Reports (single- or double-column, any student).

One tool, two redaction passes, chosen with --redact:

    --redact all      (default)  remove PII *and* redact grades
    --redact pii                 remove PII only
    --redact grades              redact grades only

Both passes run on the same in-memory document and are gated by a single
verification step, so a file is only written once it is proven clean for the
selected passes.  Output filenames encode the mode so a partial redaction can
never be mistaken for a complete one:

    all     -> REDACTED_<name>.pdf
    pii     -> REDACTED-PII_<name>.pdf
    grades  -> REDACTED-GRADES_<name>.pdf

PII pass:    student ID, roster + diploma name, mailing address, sport/team.
Grade pass:  each grade -> basis + pass/fail token (Lp/Lf/Pp/Pn); keeps
             IN/IX, RG, TR, W, CR/NC, flags; neutralizes GPA/POINTS figures.

How it stays faithful & bulletproof: it TRULY removes the target glyphs
(PyMuPDF apply_redactions) and re-inserts width-preserving monospace filler, so
the fixed-width columns are preserved and the originals are gone — not covered.

Usage:
  python3 redact_stars.py INPUT.pdf [-o OUT] [--redact all|pii|grades]
                                    [--dry-run] [--tag]
  python3 redact_stars.py FOLDER    [-o OUT_FOLDER] [--redact ...]
"""
import argparse
import os
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF is required:  pip install pymupdf --break-system-packages")

from redactors import common, pii, grades

MODE_PREFIX = {
    frozenset({"pii", "grades"}): "REDACTED_",
    frozenset({"pii"}): "REDACTED-PII_",
    frozenset({"grades"}): "REDACTED-GRADES_",
}


def _default_out(in_path, modes, out_dir=None):
    base = os.path.basename(in_path)
    base = re.sub(r"^DONOTSHARE[_-]*", "", base, flags=re.IGNORECASE)
    base = re.sub(r"^REDACTED[A-Z-]*_", "", base, flags=re.IGNORECASE)  # no stacking
    d = out_dir if out_dir else os.path.dirname(in_path)
    return os.path.join(d, MODE_PREFIX[frozenset(modes)] + base)


def process_one(in_path, out_path, modes, tag=False):
    """Redact one report for the selected passes. Returns a status dict and
    NEVER writes a file that fails verification."""
    res = {"file": in_path, "out": out_path, "modes": modes, "status": None,
           "reason": "", "pii": {}, "grades": {}, "fragments": [], "hard": []}
    doc = fitz.open(in_path)

    if not common.has_text_layer(doc):
        res["status"] = "SKIPPED"
        res["reason"] = "no text layer (scanned image; needs OCR-based redaction)"
        doc.close()
        return res

    findings, metas = [], {}
    if "pii" in modes:
        pf, pm = pii.build_findings(doc, tag=tag)
        if not pm["values"]:
            res["status"] = "FAILED"
            res["reason"] = "text present but no STARS identifiers detected"
            doc.close()
            return res
        findings += pf
        metas["pii"] = pm
        res["pii"] = pm["values"]
    if "grades" in modes:
        gf, gm = grades.build_findings(doc)
        findings += gf
        metas["grades"] = gm
        res["grades"] = gm

    common.apply_and_fill(doc, findings)
    common.scrub_metadata(doc)

    hard, soft = [], []
    if "pii" in modes:
        h, s = pii.verify(doc, metas["pii"])
        hard += h
        soft += s
    if "grades" in modes:
        h, s = grades.verify(doc, metas["grades"])
        hard += h
        soft += s
    res["fragments"] = soft

    if hard:
        res["status"] = "FAILED"
        res["reason"] = "verification failed — output withheld"
        res["hard"] = hard
        doc.close()
        return res

    doc.save(out_path, garbage=4, deflate=True, clean=True)
    doc.close()
    res["status"] = "REVIEW" if soft else "REDACTED"
    return res


def _print_one(res):
    print(f"\n=== {os.path.basename(res['file'])}  [{'+'.join(sorted(res['modes']))}] ===")
    for k, v in res.get("pii", {}).items():
        print(f"  {k:24s}: {v!r}")
    if res.get("grades"):
        g = res["grades"]
        print(f"  grades redacted: {g['grades_replaced']}  |  "
              f"GPA/POINTS figures: {g['gpa_replaced']}  |  "
              f"course rows seen: {g['course_rows']}")
    label = {"REDACTED": "OK (verified clean)", "REVIEW": "OK — needs human review",
             "SKIPPED": "SKIPPED", "FAILED": "FAILED"}[res["status"]]
    print(f"  -> {label}: {res['reason'] or res['out']}")
    for tok, pages in res["fragments"]:
        print(f"     review: name fragment {tok!r} still appears on page(s) {pages}")
    for h in res.get("hard", []):
        print(f"     !! {h}")


def run_batch(in_dir, out_dir, modes, tag=False):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for name in sorted(os.listdir(in_dir)):
        if not name.lower().endswith(".pdf") or name.upper().startswith("REDACTED"):
            continue
        src = os.path.join(in_dir, name)
        try:
            r = process_one(src, _default_out(src, modes, out_dir), modes, tag=tag)
        except Exception as e:      # unexpected -> report, keep going
            r = {"file": src, "modes": modes, "status": "FAILED",
                 "reason": f"error: {e}", "pii": {}, "grades": {},
                 "fragments": [], "hard": []}
        _print_one(r)
        results.append(r)

    order = ["REDACTED", "REVIEW", "SKIPPED", "FAILED"]
    counts = {s: sum(1 for r in results if r["status"] == s) for s in order}
    print("\n" + "=" * 60 + "\nBATCH SUMMARY  [redact: " + "+".join(sorted(modes)) + "]")
    for s in order:
        print(f"  {s:9s}: {counts[s]}")
    print(f"  outputs in: {out_dir}")
    return results


def _dry_run(path, modes):
    d = fitz.open(path)
    if not common.has_text_layer(d):
        print("No text layer (scanned image) — not viable for this tool.")
        return
    if "pii" in modes:
        values = pii.detect(d)
        print("Detected identifiers:" if values else "No identifiers detected.")
        for k, v in values.items():
            print(f"  {k:24s}: {v!r}")
    if "grades" in modes:
        _, gm = grades.build_findings(d)
        print(f"Grades to redact: {gm['grades_replaced']}  |  "
              f"GPA/POINTS figures: {gm['gpa_replaced']}  |  "
              f"course rows: {gm['course_rows']}")


def main():
    ap = argparse.ArgumentParser(
        description="Bulletproof redaction of USC STARS report(s): PII and/or grades.")
    ap.add_argument("input", help="a STARS report PDF, or a folder of them")
    ap.add_argument("-o", "--output",
                    help="output file (single) or output folder (batch)")
    ap.add_argument("--redact", choices=["all", "pii", "grades"], default="all",
                    help="what to redact (default: all = PII + grades)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be redacted and exit (writes nothing)")
    ap.add_argument("--tag", action="store_true",
                    help="use [REDACTED-*] labels instead of X filler for PII")
    args = ap.parse_args()

    modes = {"pii", "grades"} if args.redact == "all" else {args.redact}

    if os.path.isdir(args.input):
        out_dir = args.output or os.path.join(args.input, "REDACTED")
        run_batch(args.input, out_dir, modes, tag=args.tag)
        return

    if args.dry_run:
        _dry_run(args.input, modes)
        return

    res = process_one(args.input, args.output or _default_out(args.input, modes),
                      modes, tag=args.tag)
    _print_one(res)
    if res["status"] == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
