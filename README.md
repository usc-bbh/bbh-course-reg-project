# bbh-course-reg-project

## Repository layout

.
├── stars-parser/              Module 1 — STARS report parsing (JavaScript, client-side)
│   ├── index.js                 Entry point; orchestrates extraction + parsing
│   ├── textExtract.js           Direct text-layer extraction (PDF.js) — preferred path
│   ├── ocrExtract.js            OCR fallback (Tesseract.js) for scanned/imaged PDFs
│   ├── fieldParser.js           Turns extracted text into structured fields
│   ├── test/                    Fixtures + tests (PII scrubbed)
│   └── README.md
│
├── validator/                 Module 4B — next-semester validator (Python)
│   ├── validate_next_semester.py   Pure function: (planned, stars, catalog) -> result
│   ├── test/                       Fixtures + tests
│   ├── requirements-dev.txt
│   └── README.md                   Input/output schema contract
│
├── catalog/                   Module 3 — Schedule of Classes scrape (Python)
│   ├── scrape_schedule.py          Scrapes classes.usc.edu; requires USC VPN
│   ├── README.md                   Catalog schema contract + known limitations
│   └── test/
│
├── validator-gui/             Front end — schedule builder + validator UI (React)
│   └── validator_gui.jsx           Calls validate_next_semester via Pyodide
│
├── dept_clearance.json        D-clearance requirements + instructions, keyed by dept prefix
├── .gitignore
└── README.md                  You are here

## ⚠️ Note: the STARS redactor is a separate internal tool — NOT in this repo

The tool that de-identifies real STARS report PDFs (removes student PII and
replaces grades with pass/fail markers) is an **internal maintainer tool** and
is deliberately **not** part of this repository. **Do not add redaction code
here.** It lives in its own repo / Hugging Face Space, which auto-deploys the
live web app:

> **https://huggingface.co/spaces/buai-builder-hub/STARSRedacter**

That repo is the single home for the redactor — `app.py` (web UI), `redactors/`
(engine), and `redact_stars.py` (CLI). Edit redaction code there, not here.
(It previously lived under `internal-tools/` in this repo; see git history
before this commit.)
