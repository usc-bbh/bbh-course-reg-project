# STARS Report Redactor (internal tooling)

**Internal-facing utility — NOT part of the shipped BBHCourseReg app.**

This is a maintainer/data-prep tool. It takes *real* USC STARS Degree Progress
Report PDFs (which contain student PII and grades) and produces de-identified
copies that are safe to keep in the repo and use as design inputs and parser
fixtures. It is not imported by, shipped with, or run by the client-side app in
`../../stars-parser/`. Nothing here runs in a browser or touches production.

Do not commit the original, un-redacted `DONOTSHARE_*` PDFs. Run them through
this tool first and commit only the `REDACTED_*` output.

## One tool, two passes

Pick what to redact with `--redact` (default = both):

| `--redact` | Removes | Output prefix |
|---|---|---|
| `all` *(default)* | PII **and** grades | `REDACTED_` |
| `pii` | PII only | `REDACTED-PII_` |
| `grades` | grades only | `REDACTED-GRADES_` |

Both passes run on the **same in-memory document** and are gated by a **single
verification step**, so a file is only written once it is proven clean for the
selected passes. Output filenames encode the mode, so a partial redaction can
never be mistaken for a complete one.

**Passes compose.** You can run the tool on a file that was already partly
redacted: the output is named by the *cumulative* redaction. Running the grade
pass (or the default) on a `REDACTED-PII_` file skips the PII pass (nothing left
to find) and writes `REDACTED_` — i.e. PII + grades. Batch mode treats
`REDACTED-PII_` / `REDACTED-GRADES_` files as valid inputs and only skips files
already fully redacted (`REDACTED_`).

## PII pass

Detected by fixed template position/labels (never by hard-coded student data),
so it works for any student and removes every occurrence — including the
name/ID that repeat in every page header:

| Field | How it's found |
|---|---|
| Student ID | the 10-digit number in the page header |
| Roster name | the `Last, First, Middle` line under the ID header |
| Diploma name | line after "Name as it will appear on your USC Diploma:" |
| Mailing street | text after "Diploma will be mailed to:" |
| Mailing city/state/zip | the line following the street |
| Sport / team | text between "Student Athlete:" and "Clock Date:" |

Fields absent for a student (e.g. a non-athlete has no sport line) are skipped.
Works on both single- and double-column STARS layouts.

## Grade pass

Each grade is located structurally: in a course row (`term  code  [suffixes]
units  GRADE  …title`) the grade is the word immediately after the units field
(a one-decimal number like `4.0`), which cleanly separates it from the suffix
letters (L/X/G) that precede the units. The legend / grade-definition text has
no units field, so it is never touched.

Grades are redacted to **basis + pass/fail only** — the exact grade is hidden,
but the two things the 4-year degree verifier needs are preserved: the grading
*basis* (letter vs P/NP vs credit), and university-level pass/fail.

| Original | Becomes | Meaning |
|---|---|---|
| `A A- B+ B B- C+ C C- D+ D D-` | `Lp` | letter graded, passed (earns undergrad credit) |
| `F` | `Lf` | letter graded, failed |
| `P` | `Pp` | P/NP basis, passed |
| `NP` | `Pn` | P/NP basis, not passed |
| `CR` `NC` | kept | credit / no-credit basis (already no grade value) |
| `IN` `IX` `MG` `NS` | kept | incomplete / expired / missing / not submitted |
| `RG` `TR` `W` and all `>` flags | kept | in-progress / transfer / withdrawn / status flags |

It also **neutralizes the GPA and POINTS figures** — the only numbers printed
with three decimals (`3.107`, `174.000`) — to `X.XXX` / `XXX.XXX`, so grades
can't be reverse-engineered from the summaries. Unit tallies use two decimals
(`93.00 UNITS`) and are left intact, because the degree verifier needs them.

### Why "basis + pass/fail" and not finer bands

"Passing" isn't a property of the grade alone — it's grade × the requirement's
minimum × the school. The verified rules:

- **University-wide:** the minimum passing grade *for undergraduate credit is
  D-*; `F` earns no credit. `P` and `CR` mean "C- quality or better"; `NP`/`NC`
  mean below C-. `CR/NC/P/NP/W/IP/MG/IN` do not affect GPA. An `IN` lapses after
  one year to `IX` = 0 points (counted as failing).
- **Requirement-specific minimums are higher than the floor:** GE, writing, and
  most major requirements need **C- or better** (and generally can't be P/NP);
  **Viterbi** CS core courses require a **C**, with C- or below requiring a
  repeat; **Marshall** passes a course at D- but requires a 2.0 major and
  cumulative GPA. So a `D` that earns university credit still *fails* a core
  requirement demanding C-/C.

Because the maintainers chose maximum privacy, this pass intentionally does
**not** preserve the C-/C distinctions needed to enforce those stricter
per-school minimums from the redacted fixture. The degree verifier's
threshold logic (e.g. "D in a core course = retake") should be unit-tested with
purpose-built **synthetic** grade cases rather than real students' low grades.

Sources: [USC Catalogue — Academic Standards (grade definitions)](https://catalogue.usc.edu/content.php?catoid=11&navoid=3437),
[USC Viterbi / CS core-grade requirement](https://www.cs.usc.edu/academic-programs/undergrad/computer-science/),
[USC Marshall advising FAQ (repeats & grades)](https://students.marshall.usc.edu/current-students/academic-advising/faqs).

## Why it's "bulletproof" (and how it stays faithful)

A black box drawn over text is **not** redaction — the characters remain in the
text layer and come straight back out with copy/paste or any extractor. This
tool instead:

1. **Truly deletes** the target glyphs from the PDF content stream
   (PyMuPDF `apply_redactions`), so the data is gone, not covered.
2. **Re-inserts width-preserving monospace filler** sized to the original box,
   so the fixed-width column structure the parser relies on is preserved and
   every other field stays in its original position.
3. **Scrubs document metadata / XMP** (the source PDFs list a staff member as
   the author).
4. **Self-verifies before writing.** It re-extracts from the result and confirms
   every selected item is gone (no detected PII value; no raw letter/`P`/`NP`
   grade after a units field; no three-decimal GPA/POINTS number). If anything
   survives it writes **nothing** (see FAILED) — you never get a file that looks
   clean but isn't.

## Result buckets (and what the warnings mean)

Every file ends in exactly one bucket:

- **REDACTED** — everything for the selected passes removed and verified. Safe.
- **REVIEW** — redacted and verified, **but** a bare name *fragment* (a surname
  or first name on its own) still appears elsewhere. The file *is* written; the
  fragment is only flagged (with page numbers) for a human to check. It is not
  auto-erased because a token like `Law` or `Black` is usually a legitimate
  course word ("Environmental **Law**", "**Black** Europe").
- **SKIPPED** — the PDF has no text layer (a scan/photo). Nothing is written.
- **FAILED** — the PDF has text but no STARS anchors were found, or verification
  found a survivor. **Nothing is written** on FAILED. In batch mode one
  FAILED/SKIPPED file never stops the rest of the run.

## Scanned reports are not supported

Reports with **no text layer** (registrar-provided scans / photocopies — every
page is a flat image) cannot be handled here: there are no glyphs to remove and
no anchors to read, so they are auto-**SKIPPED**. Redacting those would require
a separate OCR + image-box pipeline that produces an image (no faithful text
layer) and depends on OCR accuracy. That path is intentionally **not** built.

## Requirements

- Python 3.8+
- [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`)

```bash
pip install -r requirements.txt
# or:  pip install pymupdf
```

## Usage (terminal)

**Single file** — writes a mode-prefixed file next to the input by default:

```bash
python3 redact_stars.py "path/to/DONOTSHARE_report.pdf"                 # PII + grades
python3 redact_stars.py "path/to/report.pdf" --redact pii              # PII only
python3 redact_stars.py "path/to/report.pdf" --redact grades          # grades only
python3 redact_stars.py "path/to/report.pdf" -o "path/to/OUT.pdf"     # explicit output
```

**Whole folder (batch)** — processes every PDF, skips files already named
`REDACTED*`, writes to an output folder (default: a `REDACTED/` subfolder), and
prints a per-file status plus a summary:

```bash
python3 redact_stars.py "../../../STARS Reports"
python3 redact_stars.py "../../../STARS Reports" --redact grades -o "../../../STARS Reports/REDACTED"
```

**Preview only** — see what would be redacted without writing anything:

```bash
python3 redact_stars.py "path/to/report.pdf" --dry-run
```

### Options

| Flag | Effect |
|---|---|
| `--redact all\|pii\|grades` | what to redact (default `all` = PII + grades) |
| `-o, --output` | output file (single) or output folder (batch) |
| `--dry-run` | print what would be redacted and exit; write nothing |
| `--tag` | use `[REDACTED-NAME]` labels instead of `XXXX` filler (PII only) |

### Example

```
=== DONOTSHARE_SINGLEColumn.pdf  [grades+pii] ===
  Student ID              : '...'
  Roster name             : '...'
  ...
  grades redacted: 97  |  GPA/POINTS figures: 5  |  course rows seen: 149
  -> OK (verified clean): .../REDACTED_SINGLEColumn.pdf

=== 2X_X_BUAD.pdf  [grades+pii] ===
  -> SKIPPED: no text layer (scanned image; needs OCR-based redaction)

============================================================
BATCH SUMMARY  [redact: grades+pii]
  REDACTED : 2
  REVIEW   : 0
  SKIPPED  : 11
  FAILED   : 0
```

Always spot-check any file marked **REVIEW**, and never commit a `DONOTSHARE_*`
original.

## Layout

```
internal-tools/redaction/
  redact_stars.py        # CLI orchestrator (entry point)
  redactors/
    common.py            # shared remove/refill + verify-before-write machinery
    pii.py               # PII detection + verification
    grades.py            # grade + GPA detection + verification
  requirements.txt
  README.md
```
