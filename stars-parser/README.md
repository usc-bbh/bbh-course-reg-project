# STARS Parser

Parses a USC STARS degree progress report PDF into a structured JSON object.
Built for Module 1 of the TrojanReg project.

## How it works

Two approaches, tried in order:

1. Direct text extraction via PDF.js — works for PDFs downloaded from my.usc.edu
2. OCR via Tesseract.js — fallback for scanned copies (e.g. registrar-provided anonymized reports)

If both fail, returns null so the UI can prompt the student to fill in their info manually.

Everything runs client-side. Nothing is sent to a server.

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
    { "term": "20233", "code": "BUAD304", "title": "Organizational Behavior", "units": 4.0, "grade": "A" }
  ],
  "inProgressCourses": [
    { "term": "20261", "code": "BUAD497", "title": "Strategic Management", "units": 4.0 }
  ],
  "transferUnits": 32,
  "minor": "Dance",
  "isTransfer": false,
  "studiedAbroad": true,
  "isStudentAthlete": false,
  "requirements": [
    { "label": "128-Unit Minimum", "status": "ok" },
    { "label": "64-Unit Residency", "status": "ok" }
  ]
}
```

## Usage

```js
import { parseStarsReport } from "./stars-parser";

const result = await parseStarsReport(file, {
  onStatus: (msg) => console.log(msg),
  onProgress: (page, total) => console.log(`OCR: ${page}/${total}`),
});

if (!result) {
  // prompt manual entry
}
```

## Dependencies

- pdfjs-dist
- tesseract.js

## Tests

Run the test suite with:

```
node stars-parser/test/parser.test.js
```

Tests all 10 sample reports against known ground truth — major, GPA, transfer units, flags, minors etc. No dependencies needed to run it.
