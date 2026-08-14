# bbh-course-reg-project

## Repository layout

```
.
├── stars-parser/              Module 1 — STARS report parsing (JavaScript, client-side)
│   ├── index.js                 Entry point; orchestrates extraction + parsing
│   ├── textExtract.js           Direct text-layer extraction (PDF.js) — preferred path
│   ├── ocrExtract.js            OCR fallback (Tesseract.js) for scanned/imaged PDFs
│   ├── fieldParser.js           Turns extracted text into structured fields
│   ├── test/                    Fixtures + tests (PII scrubbed)
│   └── README.md
│
├── validator/                 Module 4B — next-semester validator (Python) + its GUI
│   ├── validate_next_semester.py   Pure function: (planned, stars, catalog) -> result
│   ├── validator_gui.jsx           Front end — schedule builder + validator UI (React)
│   ├── pyodide_bridge.js           Runs validate_next_semester in the browser via Pyodide
│   ├── test/                       Fixtures + tests
│   ├── requirements-dev.txt
│   └── README.md                   Input/output schema contract
│
├── catalogue_scraper/         Module 2 — USC Catalogue scrape: degree/major/minor
│   │                            REQUIREMENTS (Python). Not the Schedule of Classes.
│   ├── src/usc_catalog_scraper/     Layered HTTP→browser acquisition, structural
│   │                                content-region selection, output validation
│   ├── tools/                       Corpus audit, runtime + repeatability checks
│   ├── data/                        470 verified programme files (2026-2027)
│   ├── macos_app/                   Double-clickable wrapper that asks for the year
│   ├── docs/                        Design guide + incident report
│   └── README.md                    Requirements schema contract
│
├── catalog/                   Module 3 — Schedule of Classes scrape (Python)
│   ├── scrape_schedule.py.py       Scrapes classes.usc.edu; requires USC VPN
│   ├── README.md                   Catalog schema contract + known limitations
│   └── test/
│
├── docs/                      Cross-module documentation
│   └── TESTING_GUIDE.md            Intro to test suites and pytest, for the team
│
├── constraint_classifier_prompt.md   Taxonomy + LLM prompt that classifies raw USC
│                                     degree-requirement text into constraint types
├── dept_clearance.json        D-clearance requirements + instructions, keyed by dept prefix
├── DEPT_CLEARANCE_SOURCES.md  Where the D-clearance data came from, and how to refresh it
├── .gitignore
└── README.md                  You are here
```

### Schema contracts — read these before wiring modules together

Each module owns and documents the shape of the data it produces. A consumer should
read the producer's own README rather than infer the shape from its code:

| Data | Documented in |
|---|---|
| Parsed STARS output | `validator/README.md` — documents the `stars_summary` slice the next-semester validator consumes (explicitly *not* the full parser output) |
| Degree/major/minor requirements | `catalogue_scraper/README.md` |
| Schedule of Classes / course catalog | `catalog/README.md` |
| D-clearance | `dept_clearance.json` (`_schema_version`); provenance in `DEPT_CLEARANCE_SOURCES.md` |
| Requirement constraint types | `constraint_classifier_prompt.md` §6, Taxonomy reference |

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
