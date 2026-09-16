# STARS Parser

Parses a USC STARS degree progress report PDF into a structured JSON object.
Built for Module 1 of the TrojanReg project.

## Scope

Supports **only** the single-column PDF a student gets by doing print-to-PDF
from `experience.usc.edu`. That export always has a real text layer (it's
not a scan), so parsing is direct text extraction — no OCR.

Explicitly out of scope, per [`docs/parser-brief.md`](../docs/parser-brief.md) §3:

- Scanned/imaged PDFs with no text layer.
- The two-column layout some STARS variants use — Registrar-only; students
  never see it.
- Reports from USC systems other than `experience.usc.edu`.

Everything runs client-side. Nothing is sent to a server. If the PDF has no
text layer, or doesn't parse as a STARS report, `parseStarsReport` returns
`null` so the UI can prompt the student to fill in their info manually.

## How it works

1. `textExtract.js` reads the PDF's text layer via PDF.js and rebuilds each
   page's fragments into real lines (`lineRebuilder.js`) — a PDF stores
   positioned fragments, not lines, so this has to happen before anything
   else can work.
2. `chunker.js` cuts the rebuilt text into labelled chunks (master course
   list, "other courses in your academic account", NCAA section, etc.), so
   course extraction only ever reads from the two chunks that are actually
   the student's course record — never a requirement block repeating a
   course, or the NCAA section re-listing coursework for an athletics audit
   (parser-brief §8–9).
3. `fieldParser.js` runs field patterns against the rebuilt text (and, for
   course rows specifically, the chunked course text) to produce the
   structured output below.

If an expected landmark is missing — no major, no class level, no GPA, no
master course list — parsing throws a `StarsParseError` naming what's
missing, rather than returning a partial object. See parser-brief §10.

## Output

```json
{
  "degree": "BS",
  "major": "Business Administration",
  "concentration": "Finance",
  "majorCode": "BFIN",
  "programCode": "1833",
  "catalogYear": "2023-2024",
  "classLevel": "Senior",
  "expectedGraduation": "16 December 2026",
  "gpa": 3.74,
  "upperDivisionGpa": 3.84,
  "completedCourses": [
    { "term": "20233", "code": "BUAD304", "title": "Organizational Behavior", "units": 4.0, "grade": "A", "source": "usc" },
    { "term": "20233", "code": "ESRM150", "title": "Statistics Transfer Equivalent", "units": 4.0, "grade": "TR", "source": "transfer_specific" },
    { "term": "20241", "code": "TR-PSYC", "title": "General Psychology Transfer", "units": 3.0, "grade": "TR", "source": "transfer_generic" }
  ],
  "inProgressCourses": [
    { "term": "20261", "code": "BUAD497", "title": "Strategic Management", "units": 4.0, "grade": "RG", "source": "usc" }
  ],
  "transferUnits": 32,
  "minor": "Dance",
  "isTransfer": false,
  "studiedAbroad": true,
  "isStudentAthlete": false,
  "requirements": [
    { "label": "128-Unit Minimum", "status": "ok" },
    { "label": "64-Unit Residency", "status": "ok" }
  ],
  "warnings": []
}
```

`source` on each course is one of:

- `"usc"` — a course actually taken at USC.
- `"transfer_specific"` — transfer credit USC mapped to a specific USC
  course code (shows `TR` in the grade column).
- `"transfer_generic"` — transfer credit with no USC equivalent, e.g.
  `TR-PSYC`. Counts toward the 128-unit total but can't satisfy a
  prerequisite or a named requirement (parser-brief §7).

`warnings` is a best-effort self-check: if the parsed course list's units
don't reconcile with the report's own `EARNED: ... UNITS` total, a note goes
here rather than failing silently or hard-erroring on something that might
just be an unmodeled edge case (e.g. deleted/excluded-credit flags).

## Usage

```js
import { parseStarsReport } from "./stars-parser";

const result = await parseStarsReport(file, {
  onStatus: (msg) => console.log(msg),
});

if (!result) {
  // prompt manual entry — no text layer, or not a supported STARS format
}
```

## Dependencies

- pdfjs-dist

## Tests

```
node --test stars-parser/test/*.test.js
```

`lineRebuilder.test.js` and `chunker.test.js` import the real modules
(`lineRebuilder.js`, `chunker.js`, `fieldParser.js`) rather than holding
copies of their logic, per parser-brief §12.

Fixtures in `test/fixtures/` are hand-built single-column samples, not real
student data — see [`CONTRIBUTING.md`](../CONTRIBUTING.md) for why nothing
extracted from a real report is ever committed here. They haven't been
checked against a real `experience.usc.edu` export yet; if a real report
doesn't chunk or parse the way these fixtures assume, the report wins.
