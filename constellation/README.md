> **OPEN QUESTION: should Constellation share the STARS parser with TrojanReg?** Constellation uses its own parser (`src/parser.js`). TrojanReg uses `stars-parser/`. Sharing one parser is an option we haven't decided on. See [Parser strategy](#parser-strategy) for the trade-offs.

# Constellation

**Make sense of your STARS.** Turns a USC STARS report into a clear, readable summary.

A student or advisor opens the page, drops in a STARS report PDF, and gets one page showing what's done, what's in progress, and exactly what's left. It's easier to read than the raw report, and the original text is one click away for cross-checking.

Owner: Natalie. Constellation is its own project. It can be used next to RegCheck and the degree planner, but it doesn't depend on them.

## Privacy: nothing leaves the device

- **Zero network requests.** Everything the page needs is inside `index.html`: pdf.js, the fonts, the parser, and the sample report. Once it's open, it works offline.
- **Enforced by the browser.** The page's Content-Security-Policy blocks every outgoing connection (`connect-src 'none'`, `default-src 'none'`). Scripts run only if their hash matches the build, so a script added later without a rebuild won't run.
- **Nothing stored.** No cookies, localStorage, or IndexedDB. Closing the tab or clicking "Summarize another report" clears everything, which matters for advisors on shared computers.
- **Redacted before reading.** The name, student ID, and diploma name and mailing address are removed before parsing. The test checks this on every report.
- **Never committed.** Reports and anything derived from them (including test expected results) are git-ignored. `npm run check:privacy` also fails if one is tracked or staged, because `.gitignore` doesn't stop `git add -f`.

`npm run check:privacy` checks all of this. It runs as part of `npm test`.

## What's in this folder

| Path | What it is |
| --- | --- |
| `index.html` | The built page (about 2 MB, self-contained). Open it in a browser. |
| `src/parser.js` | The STARS parser: report text in, requirement tree, deduplicated course list, and "what's left" list out. |
| `src/pdftext.js` | PDF to text: runs pdf.js and rebuilds lines. Shared by the page and the test so both run the same code. |
| `src/page.html` | The page template: layout, styles, rendering. |
| `src/sample-report.txt` | A fictional report behind the "Try a sample report" button. |
| `build.js` | Builds `index.html`: inlines everything, bundles pdf.js from `node_modules`, embeds the fonts, writes the CSP. |
| `scripts/check-privacy.mjs` | The privacy check described above. |
| `test/run.mjs` | Runs every PDF in `test/samples/` through the same pipeline as the page. |

## Working on it

```
npm install
npm run build          # after editing anything in src/
npm test               # builds, runs the privacy check, then tests every report in test/samples/
```

pdf.js is pinned to one exact version (`pdfjs-dist` 4.10.38) in `package.json`. The page and the test both use it. Upgrade it on purpose and re-run every report.

## Parser strategy

**Now:** Constellation keeps its own parser in `src/parser.js`. It doesn't import `stars-parser/`.

**Why it's separate:** Constellation needs the full requirement tree: every block and sub-requirement with its STARS status (OK/NO/IP, +/-), "pick N of M" rules, OR alternatives, and course options. That's what powers the checklist and the "what's left" list. `stars-parser/` outputs profile fields (major, GPA, completed courses, flags) for TrojanReg and doesn't produce that tree. Keeping them separate also means a Constellation change can't break RegCheck, which pins `stars-parser/` through a git submodule.

**Things to weigh before deciding whether to share:**

- *For sharing:* one parser to fix when STARS changes format; one anonymized test set; no duplicate effort (the lead has already flagged duplicate STARS parsers across repos).
- *Against sharing:* the two tools need different outputs; RegCheck's pin and release cadence would constrain Constellation; `stars-parser/` has an OCR fallback (Tesseract.js) that Constellation doesn't need and that would add megabytes to a zero-request page.
- *Middle options:* (a) share only the redaction and line-rebuilding steps; (b) add requirement-tree output to `stars-parser/` and have Constellation import it; (c) test both parsers against the same anonymized reports and compare the fields they both produce (major, catalog year, GPA, courses), without merging code.
- *Signals it's time to revisit:* `stars-parser/` starts producing requirement blocks; STARS changes format and both parsers need the same fix; or the two disagree on the same report.

Until this is decided, raise parser changes with Tanzil (who owns `stars-parser/`) whenever they touch shared ground, like redaction or line rebuilding.

## Testing now

1. Put the anonymized PDFs in `test/samples/`. That folder is git-ignored; never commit reports or anything generated from them.
2. Run `npm test`. For each report it first checks **redaction**: the name, any 10-digit ID, and every line of the diploma and mailing block must not appear in the parsed result or in the report text the page shows. A failure prints `LEAK` (without printing the values).
3. For a new report it writes `test/expected/<name>.draft.json`: major, catalog year, GPA, major GPA, units (earned, in progress, needed), which fields were redacted, course count, every block's status and its sub-requirement statuses, and the "what's left" list.
4. Check each draft against the PDF by hand. Then have a second person check it too, so one person's misreading doesn't become the answer key. When it's right, rename it to `<name>.json`.
5. From then on, `npm test` prints PASS or FAIL per report. A failure writes `<name>.actual.json` next to it so you can diff the two.

Expected results stay local too, because they record a real student's major, courses, and GPA. Share them the same way as the anonymized PDFs, never through git.

## More thorough testing later

The current test proves the parser handles a few reports. Before recommending Constellation widely, testing should show it handles the range of reports students actually have. Here's how that would work:

1. **Coverage matrix.** List the dimensions that change a report's structure, then collect at least one anonymized report per cell that matters:
   - school (Dornsife, Marshall, Viterbi, Annenberg, and so on) and degree type (BA, BS)
   - catalog year (older catalogs use older GE rules)
   - GE track: Core Literacies, Thematic Option, and older GE programs
   - transfer credit, AP/IB credit, and foreign language waivers
   - minors, double majors, and progressive degrees
   - substitutions and waivers (RE, RA, CW, UW, RW)
   - repeated, pass/no pass, incomplete, and deleted-credit courses
   - reports from freshmen (mostly "needs") through graduating seniors (mostly "done")

   Keep the matrix in this README with the report name in each cell, so gaps are visible.
2. **Field-level checks.** Replace the single whole-summary comparison with one check per field (units, GPA, each block, each course), so a failure names what broke instead of just saying "FAIL".
3. **Per-course checks.** Check every course's term, code, units, grade, and flags against the PDF, not just the course count.
4. **Cross-checks that need no answer key.** Rules that must hold for any report: every "done" block has no "needs" sub-requirements; units in the course list, minus in-progress, repeated, and deleted-credit courses, match STARS's earned total; every course in a "what's left" option list is a real course code; the page shows every block the parser found.
5. **Side-by-side review.** For each report in the matrix, someone who knows STARS (ideally an advisor) compares the rendered page to the PDF and records disagreements as new test cases.
6. **Stress inputs.** Scanned PDFs, a report printed from a different browser, a partial report (missing "END OF ANALYSIS"), non-STARS PDFs, and very long reports. Each should show a clear message, never a wrong summary.
7. **Compare with `stars-parser/`.** Run both parsers on the same reports and compare the fields both produce. This works whichever way the [open question](#parser-strategy) is decided.

## How it works

1. **Read the PDF.** pdf.js (bundled, running in an in-memory worker) pulls text fragments, which are regrouped into lines by vertical position (`src/pdftext.js`).
2. **Redact.** Name, student ID, and diploma address are removed first. Browser print headers and footers and anonymizer artifacts ("X.XXX", "Lp") are dropped.
3. **Parse.** Sections are split on the `____` rules. Every status comes from STARS's own codes (OK, NO, IP on blocks; +, -, IP+, IP- on sub-requirements), never from guessing.
4. **Render.** A summary dashboard (units, items left, GPA), progress by area with every requirement and its status, a "what's left" table, the full checklist, course history, and the original text for cross-checking. It prints cleanly to PDF.

## Tested on

Hand-checked on three anonymized reports during v0.1. That was before the switch from pdf.js 3.11 (loaded from a CDN) to the bundled 4.10, so re-run `npm test` on them.

- AI for Business (BS), catalog Fall 2024
- Psychology (BA), catalog Fall 2026, Thematic Option
- Computational Neuroscience (BS), catalog Fall 2026

Formats handled: Core Literacies and Thematic Option GE, the Dornsife 104-unit and 40-unit department cap blocks, foreign language waivers, multiple major blocks, "pick N of M" categories, sub-requirements with no +/- marker, "OR" alternatives, wrapped course lists, and course ranges.

## Roadmap

- **V1 (this):** a single self-contained web page.
- **V2: Chrome extension.** Same parser and rendering, opened from the browser toolbar. Chrome's extension rules (Manifest V3) don't allow inline scripts or code loaded from the internet. Bundling pdf.js already covers the second. For the first, `build.js` will need a mode that writes the scripts as separate files. `src/` is kept split into modules for that reason. The extension should ask for no host permissions: the student picks the file, just like on the page.

## Known limits

- Scanned PDFs with no text layer are rejected with a message. OCR (as in `stars-parser/ocrExtract.js`) would add several megabytes and would need to be bundled, not loaded from a CDN.
- STARS cuts course titles at 29 characters. The page marks them with "…"; full titles need the course catalog.
- `index.html` is about 2 MB because pdf.js and the fonts are inside it. That's the cost of making zero requests.
- Fonts: Bricolage Grotesque and IBM Plex Sans, both under the SIL Open Font License, embedded from the `@fontsource` packages.
- Unofficial. STARS and the student's academic advisor are the source of truth for graduation.
