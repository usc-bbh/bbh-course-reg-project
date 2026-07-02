# STARS Report Redactor (internal tooling)

**Internal-facing utility — NOT part of the shipped BBHCourseReg app.**

This is a maintainer/data-prep tool. It takes *real* USC STARS Degree Progress
Report PDFs (which contain student PII) and produces de-identified copies that
are safe to keep in the repo and use as design inputs and parser fixtures.
It is not imported by, shipped with, or run by the client-side app in
`../../stars-parser/`. Nothing here runs in a browser or touches production.

Do not commit the original, un-redacted `DONOTSHARE_*` PDFs. Run them through
this tool first and commit only the `REDACTED_*` output.

## What it removes

Detected by their fixed template position/labels (never by hard-coded student
data), so it works for any student:

| Field                | How it's found                                        |
|----------------------|-------------------------------------------------------|
| Student ID           | the 10-digit number in the page header                |
| Roster name          | the `Last, First, Middle` line under the ID header    |
| Diploma name         | line after "Name as it will appear on your USC Diploma:" |
| Mailing street       | text after "Diploma will be mailed to:"               |
| Mailing city/state/zip | the line following the street                       |
| Sport / team         | text between "Student Athlete:" and "Clock Date:"     |

Any field that is absent for a given student (e.g. a non-athlete has no sport
line) is simply skipped. Works on both the single-column and double-column
STARS layouts, and removes every occurrence — including the name/ID that repeat
in the header of every page.

## Why it's "bulletproof" (and how it stays faithful)

A black box drawn over text is **not** redaction — the characters remain in the
text layer and come straight back out with copy/paste or any extractor. This
tool instead:

1. **Truly deletes** the target glyphs from the PDF content stream
   (PyMuPDF `apply_redactions`), so the PII is gone, not covered.
2. **Re-inserts an equal-length monospace `X` filler** sized to the original
   box, so the fixed-width column structure the parser relies on is preserved
   and every other field stays in its original position.
3. **Scrubs document metadata / XMP** (the source PDFs list a staff member as
   the author).
4. **Self-verifies before writing.** It re-extracts text from the result and
   confirms every detected value is gone. If anything survives, it writes
   **nothing** (see FAILED below) — you never get a file that looks clean but
   isn't.

## Result buckets (and what the warnings mean)

Every file ends in exactly one bucket:

- **REDACTED** — all identifiers removed and verified gone. Safe to use.
- **REVIEW** — redacted and verified, **but** a bare name *fragment* (a surname
  or first name on its own) still appears somewhere else in the report. The
  file *is* written; the fragment is only flagged (with page numbers) for a
  human to check. It is not auto-erased because a token like `Law` or `Black`
  is usually a legitimate course word ("Environmental **Law**", "**Black**
  Europe"), and blindly deleting it would corrupt the report.
- **SKIPPED** — the PDF has no text layer (a scan/photo). Nothing is written.
- **FAILED** — the PDF has text but no STARS anchors were found, or a full
  identifier survived verification. **Nothing is written** on FAILED. In batch
  mode one FAILED/SKIPPED file never stops the rest of the run.

## Scanned reports are not supported

Reports with **no text layer** (registrar-provided scans / photocopies — every
page is a flat image) cannot be handled here: there are no glyphs to remove and
no anchors to read, so they are auto-**SKIPPED**. Redacting those would require
a separate OCR + image-box pipeline that produces an image (no faithful text
layer) and depends on OCR accuracy. That path is intentionally **not** built in
this tool. For scanned files, redact by hand or use dedicated image-redaction
software.


## Requirements

- Python 3.8+
- [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`)

```bash
pip install -r requirements.txt
# or:  pip install pymupdf
```

## Usage (terminal)

**Single file** — writes `REDACTED_<name>.pdf` next to the input by default:

```bash
python3 redact_stars.py "path/to/DONOTSHARE_report.pdf"
# choose the output path explicitly:
python3 redact_stars.py "path/to/report.pdf" -o "path/to/REDACTED_report.pdf"
```

**Whole folder (batch)** — point it at a directory; it processes every PDF,
skips files already named `REDACTED_*`, writes results to an output folder
(default: a `REDACTED/` subfolder), and prints a per-file status plus a summary:

```bash
python3 redact_stars.py "../../../STARS Reports"
# or set the output folder:
python3 redact_stars.py "../../../STARS Reports" -o "../../../STARS Reports/REDACTED"
```

**Preview only** — see what would be detected without writing anything:

```bash
python3 redact_stars.py "path/to/report.pdf" --dry-run
```

**Options**

| Flag         | Effect                                                        |
|--------------|--------------------------------------------------------------|
| `-o, --output` | output file (single) or output folder (batch)              |
| `--dry-run`  | print detected identifiers and exit; write nothing           |
| `--tag`      | use `[REDACTED-NAME]` style labels instead of `XXXX` filler  |

### Example batch output

```
=== DONOTSHARE_SINGLEColumn.pdf ===
  Student ID              : '...'
  Roster name             : '...'
  ...
  -> OK (verified clean): .../REDACTED/REDACTED_SINGLEColumn.pdf

=== 2X_X_BUAD.pdf ===
  -> SKIPPED: no text layer (scanned image; needs OCR-based redaction)

============================================================
BATCH SUMMARY
  REDACTED : 2
  REVIEW   : 0
  SKIPPED  : 11
  FAILED   : 0
```

Always spot-check any file marked **REVIEW**, and never commit a `DONOTSHARE_*`
original.
