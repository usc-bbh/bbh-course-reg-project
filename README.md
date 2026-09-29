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
│   ├── reference/                  Background on USC degree requirements and the
│   │                               STARS report — start here if you're new
│   └── TESTING_GUIDE.md            Intro to test suites and pytest, for the team
│
├── fixtures/stars/            Shared STARS fixtures — each <name>.json is the parser's
│                              expected output AND the validator's stars_summary input
├── degree-planner/            Four-year degree planner UI (React + TypeScript)
├── constraint_classifier_prompt.md   Taxonomy + LLM prompt that classifies raw USC
│                                     degree-requirement text into constraint types
├── .gitignore
└── README.md                  You are here
```

### Module 4B — the next-semester validator lives in its own repo

The validator (Python, plus the RegCheck web app that runs it via Pyodide)
lives only in [usc-bbh/next-sem-validator](https://github.com/usc-bbh/next-sem-validator), deployed at
https://usc-bbh.github.io/next-sem-validator/. Fix validator bugs there.
RegCheck imports `stars-parser/` from *this* repo through a pinned git
submodule, so `stars-parser/` here is the parser's only home — after a parser
fix merges, bump the pin in RegCheck (its README has the two commands).

### New to the project? Start with the reference docs

[`docs/reference/`](docs/reference/) explains USC's degree requirements and how to read a STARS
report — the domain knowledge the code assumes. It describes USC rather than this repository, so
it stays useful as the modules change. Claims carry provenance tags (`[verified]`, `[inferred]`,
`[confirm]`); the open questions at the end of each document are real, not decoration.

### Schema contracts — read these before wiring modules together

Each module owns and documents the shape of the data it produces. A consumer should
read the producer's own README rather than infer the shape from its code:

| Data | Documented in |
|---|---|
| Parsed STARS output | `stars-parser/README.md` (full parser output); [`analytics/README.md`](https://github.com/usc-bbh/next-sem-validator/blob/main/analytics/README.md) in next-sem-validator documents the `stars_summary` slice the next-semester validator consumes (explicitly *not* the full parser output) |
| Degree/major/minor requirements | `catalogue_scraper/README.md` |
| Schedule of Classes / course catalog | `catalog/README.md` |
| D-clearance | [`analytics/data/dept_clearance.json`](https://github.com/usc-bbh/next-sem-validator/blob/main/analytics/data/dept_clearance.json) in next-sem-validator (`_schema_version`) |
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
