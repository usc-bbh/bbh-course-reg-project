#!/usr/bin/env python3
"""
redact_stars.py  —  Generic, bulletproof de-identification for USC STARS
Degree Progress Reports (single-column OR double-column, any student).

It detects the student-identifying fields by their *template anchors*
(constant labels / formats), never by hard-coded student data, then:
  1. TRULY removes the underlying glyphs (PyMuPDF apply_redactions),
     not a black box on top;
  2. re-inserts an equal-length monospace "X" filler sized to the
     original box, so the fixed-width column structure is preserved;
  3. scrubs document metadata (author/producer/etc.);
  4. self-verifies with independent re-extraction and REFUSES to save
     if any detected value survives anywhere in the output.

Fields detected & removed:
  - Student ID            (10-digit number in the page header)
  - Roster name           ("Last, First, Middle" line under the ID header)
  - Diploma name          (line after "Name as it will appear on your USC Diploma:")
  - Mailing street        (after "Diploma will be mailed to:")
  - Mailing city/state/zip (the line following the street)
  - Sport / team          (between "Student Athlete:" and "Clock Date:")

Any field that is absent for a given student (e.g. a non-athlete) is
simply skipped. Nothing student-specific is hard-coded in this file.

Usage:
  python3 redact_stars.py INPUT.pdf [-o OUTPUT.pdf] [--dry-run] [--tag]
    --dry-run  : print detected PII values and exit (no file written)
    --tag      : use labels like [REDACTED-NAME] instead of X filler
"""
import argparse
import os
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF is required:  pip install pymupdf --break-system-packages")


# ---------- helpers -------------------------------------------------------
def _first_chunk(s):
    """Text up to the first run of 2+ spaces or a column separator '|'."""
    s = s.split("|", 1)[0]
    return re.split(r"\s{2,}", s.strip(), 1)[0].strip()


def _layout_lines(doc):
    """Full document as layout-preserving lines (keeps column '|' + gaps)."""
    lines = []
    for page in doc:
        # 'text' with preserve-whitespace keeps the fixed-width structure
        txt = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        lines.extend(txt.splitlines())
    return lines


CITY_RE = re.compile(r"^[A-Za-z .'\-]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?\b")
ID_RE = re.compile(r"\b\d{9,10}\b")
# a "Last, First[, Middle]" style token: alphabetic words separated by commas
ROSTER_RE = re.compile(r"^[A-Z][A-Za-z.'\-]+(?:,\s+[A-Za-z.'\-]+){1,3}$")


def detect_pii(doc):
    """Return dict {label: value} of detected identifiers, using template
    anchors only. Missing fields are omitted."""
    lines = _layout_lines(doc)
    found = {}

    # --- Student ID: first 9-10 digit number in the header region --------
    id_line_idx = None
    for i, ln in enumerate(lines[:8]):
        m = ID_RE.search(ln)
        if m:
            found["Student ID"] = m.group(0)
            id_line_idx = i
            break

    # --- Roster name: first line AFTER the ID line shaped Last, First[, M]-
    if id_line_idx is not None:
        for ln in lines[id_line_idx + 1: id_line_idx + 4]:
            cand = _first_chunk(ln)
            if cand and ROSTER_RE.match(cand):
                found["Roster name"] = cand
                break

    # --- single pass over all lines for the labelled anchors -------------
    for i, ln in enumerate(lines):
        low = ln.lower()

        if "name as it will appear on your usc diploma" in low and "Diploma name" not in found:
            # value = next non-empty line
            for nxt in lines[i + 1: i + 5]:
                cand = _first_chunk(nxt)
                if cand:
                    found["Diploma name"] = cand
                    break

        if "diploma will be mailed to:" in low and "Mailing street" not in found:
            after = ln.split(":", 1)[1] if ":" in ln else ""
            street = _first_chunk(after)
            if street:
                found["Mailing street"] = street
            # city/state/zip = the next non-empty line matching the pattern
            for nxt in lines[i + 1: i + 4]:
                cand = _first_chunk(nxt)
                if cand and CITY_RE.match(cand):
                    found["Mailing city/state/zip"] = cand
                    break

        if "student athlete:" in low and "Sport/team" not in found:
            m = re.search(r"student athlete:\s*(.*?)\s*(?:clock date:|$)", ln,
                          re.IGNORECASE)
            if m and m.group(1).strip():
                found["Sport/team"] = m.group(1).strip()

    return found


def _filler(value, tag_label=None):
    if tag_label:
        t = f"[REDACTED-{tag_label}]"
        # pad/truncate toward original length to limit column drift
        return t
    return "X" * len(value)


TAG_MAP = {
    "Student ID": "ID", "Roster name": "NAME", "Diploma name": "NAME",
    "Mailing street": "ADDRESS", "Mailing city/state/zip": "ADDRESS",
    "Sport/team": "SPORT",
}


def process_one(in_path, out_path, tag=False):
    """Redact one report. Returns a status dict; NEVER writes an unverified
    file and NEVER raises for expected conditions (scanned/no-anchor)."""
    res = {"file": in_path, "out": out_path, "status": None, "reason": "",
           "pii": {}, "fragments": [], "missing": []}
    doc = fitz.open(in_path)

    # A scanned/image-only report has no text layer -> this tool cannot help.
    total_chars = sum(len(p.get_text("text")) for p in doc)
    if total_chars == 0:
        res["status"] = "SKIPPED"
        res["reason"] = "no text layer (scanned image; needs OCR-based redaction)"
        doc.close()
        return res

    pii = detect_pii(doc)
    res["pii"] = pii
    if not pii:
        res["status"] = "FAILED"
        res["reason"] = "text present but no STARS identifiers detected"
        doc.close()
        return res

    # ---- locate + redact every occurrence of every detected value -------
    fillers = []
    for label, value in pii.items():
        hits = 0
        for pno, page in enumerate(doc):
            for r in page.search_for(value, quads=False):
                page.add_redact_annot(fitz.Rect(r), fill=(1, 1, 1))
                fillers.append((pno, fitz.Rect(r),
                                _filler(value, TAG_MAP[label] if tag else None)))
                hits += 1
        if hits == 0:
            res["missing"].append((label, value))

    for page in doc:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    for pno, r, text in fillers:
        page = doc[pno]
        n = max(len(text), 1)
        fs = min((r.width / n) / 0.6, r.height)
        page.insert_text((r.x0, r.y1 - r.height * 0.18), text,
                         fontname="cour", fontsize=fs, color=(0, 0, 0))
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass

    # ---- verify on the IN-MEMORY doc BEFORE writing anything ------------
    per_page = [p.get_text("text") for p in doc]
    corpus = "\n".join(per_page).lower()
    residual = [(k, v) for k, v in pii.items() if v.lower() in corpus]
    md = doc.metadata
    meta_leak = any(isinstance(val, str) and val
                    and any(v.lower() in val.lower() for v in pii.values())
                    for val in md.values())

    # SOFT: bare name fragments elsewhere (possible coincidental course words)
    tokens = set()
    for label in ("Roster name", "Diploma name"):
        if label in pii:
            for tok in re.split(r"[,\s]+", pii[label]):
                if len(tok) >= 4 and tok.isalpha():
                    tokens.add(tok.lower())
    for tok in sorted(tokens):
        pages = [i + 1 for i, t in enumerate(per_page) if tok in t.lower()]
        if pages:
            res["fragments"].append((tok, pages))

    if residual or meta_leak or res["missing"]:
        res["status"] = "FAILED"
        res["reason"] = ("full identifier survived verification"
                         if (residual or meta_leak)
                         else "a detected value could not be located on any page")
        res["residual"] = residual
        doc.close()
        return res   # nothing written -> no unsafe output

    doc.save(out_path, garbage=4, deflate=True, clean=True)
    doc.close()
    res["status"] = "REVIEW" if res["fragments"] else "REDACTED"
    return res


def _print_one(res):
    print(f"\n=== {os.path.basename(res['file'])} ===")
    if res["pii"]:
        for k, v in res["pii"].items():
            print(f"  {k:24s}: {v!r}")
    tag = {"REDACTED": "OK (verified clean)", "REVIEW": "OK — needs human review",
           "SKIPPED": "SKIPPED", "FAILED": "FAILED"}[res["status"]]
    print(f"  -> {tag}: {res['reason'] or res['out']}")
    for tok, pages in res["fragments"]:
        print(f"     review: name fragment {tok!r} still appears on page(s) {pages}")


def _default_out(in_path, out_dir=None):
    base = os.path.basename(in_path)
    base = re.sub(r"^DONOTSHARE[_-]*", "", base, flags=re.IGNORECASE)
    d = out_dir if out_dir else os.path.dirname(in_path)
    return os.path.join(d, "REDACTED_" + base)


def run_batch(in_dir, out_dir, tag=False):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for name in sorted(os.listdir(in_dir)):
        if not name.lower().endswith(".pdf"):
            continue
        if name.upper().startswith("REDACTED_"):
            continue
        src = os.path.join(in_dir, name)
        try:
            r = process_one(src, _default_out(src, out_dir), tag=tag)
        except Exception as e:      # unexpected -> report, keep going
            r = {"file": src, "status": "FAILED", "reason": f"error: {e}",
                 "pii": {}, "fragments": [], "missing": []}
        _print_one(r)
        results.append(r)

    order = ["REDACTED", "REVIEW", "SKIPPED", "FAILED"]
    counts = {s: sum(1 for r in results if r["status"] == s) for s in order}
    print("\n" + "=" * 60 + "\nBATCH SUMMARY")
    for s in order:
        print(f"  {s:9s}: {counts[s]}")
    print(f"  outputs in: {out_dir}")
    return results


def main():
    ap = argparse.ArgumentParser(
        description="Bulletproof de-identify USC STARS report(s), single file or folder.")
    ap.add_argument("input", help="a STARS report PDF, or a folder of them")
    ap.add_argument("-o", "--output",
                    help="output file (single) or output folder (batch)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print detected identifiers and exit (no file written)")
    ap.add_argument("--tag", action="store_true",
                    help="use [REDACTED-*] labels instead of X filler")
    args = ap.parse_args()

    if os.path.isdir(args.input):
        out_dir = args.output or os.path.join(args.input, "REDACTED")
        run_batch(args.input, out_dir, tag=args.tag)
        return

    if args.dry_run:
        d = fitz.open(args.input)
        if sum(len(p.get_text("text")) for p in d) == 0:
            print("No text layer (scanned image) — not viable for this tool.")
            return
        pii = detect_pii(d)
        print("No identifiers detected." if not pii else "Detected identifiers:")
        for k, v in pii.items():
            print(f"  {k:24s}: {v!r}")
        return

    res = process_one(args.input, args.output or _default_out(args.input), tag=args.tag)
    _print_one(res)
    if res["status"] == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    main()
