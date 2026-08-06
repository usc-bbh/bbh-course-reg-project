# USC Catalogue Scraper — how it works, how it was tested, and how to rebuild it

A teaching document. Read top to bottom: each section explains **why** a decision
was made, not just what the code does. If you understand §2 and §7 you can
rebuild the whole thing.

---

## 1. What the system does

**Goal:** turn USC's online catalogue into one plain-text file per undergraduate
programme, suitable for feeding a degree-requirements validator.

**Input:** a catalogue year (e.g. 2026-2027).
**Output:** a folder of ~470 `.txt` files (207 bachelor's programmes + 263 minors)
plus CSVs that account for every link the scraper saw and every decision it made.

One output file looks like this — a metadata header, a marker line, then the
faithfully rendered programme content:

```
Program Name: Environmental Science and Health (BA)
Credential: BA
Catalogue Year: 2026-2027
Program Identifier: poid=31805
Source URL: https://catalogue.usc.edu/preview_program.php?catoid=22&poid=31805
Acquisition Mode: direct_html
Content SHA-256: 991523b32...
Extraction Status: complete

OFFICIAL CATALOGUE CONTENT

# Environmental Science and Health (BA)
...
- BISC 120Lg General Biology: Organismal Biology and Evolution Units: 4
## Total units: 52
```

---

## 2. The four hard problems (this is the real content)

Anyone can write `requests.get(url)` and `soup.get_text()`. That produces garbage
here. Four problems make this genuinely difficult, and each one shaped the design.

### Problem 1 — "Which page is the current catalogue?" is not obvious

USC hosts every year simultaneously, keyed by an opaque `catoid`. The naive
assumption "bigger catoid = newer year" is **false**: 2023-24 is catoid 18,
2024-25 is catoid 20, 2022-23 is 16. And the site's own front page can be
*stale* — it served a cached page showing last year as current.

**Design rule that follows:** never infer. Read USC's own archive list
(`misc/catalog_list.php`), take the edition **not** marked `[ARCHIVED]`, then
*corroborate* the year against the title on that catalogue's own home page, then
find the Programs page via the site's own navigation link text. Three independent
first-party confirmations. If any step fails, say so instead of guessing.

**Generalisable lesson:** when scraping, prefer evidence the site states about
itself over patterns you noticed.

### Problem 2 — HTTP 200 does not mean you got the page

The catalogue sits behind an AWS WAF. Request a programme page with a plain HTTP
client and you get **HTTP 202 with a zero-length body** and the header
`x-amzn-waf-action: challenge`. Other times you get a JavaScript shell, or a
verification page, all with cheerful status codes.

**Design rule:** validate every response *semantically* before trusting it. Ask
the response to prove it is the page you wanted: does it contain the catalogue
title, a programme heading, course codes, requirement vocabulary? Then escalate
in layers only as needed:

```
Layer 1  plain HTTP (fast, ~2s)
Layer 2  first-party alternate representations (print variants)
Layer 3  real Chromium via Playwright (slow, ~10-60s, solves the JS challenge)
Layer 4  human hand-off (visible browser) — only if a real CAPTCHA appears
```

**The subtle part:** the WAF token *rotates roughly hourly*. When the browser
solves a challenge it receives fresh cookies — and those must be handed **back**
to the fast HTTP client after *every* browser success, not just the first. We
learned this the hard way: with a once-only cookie sync, a run started at ~5
seconds per page and degraded to 5–10 *minutes* per page after the first hour,
because every page was paying the full browser cost forever.

### Problem 3 — Deciding *what counts* is a judgement problem, not a parsing problem

"Undergraduate programme" sounds crisp. The catalogue contains ~1,150 links:
bachelor's degrees, minors, certificates, master's, doctorates, joint degrees,
progressive degrees, and combined `BS/MS` programmes.

Traps we hit, each of which produced a rule:

| Trap | Why naive code fails | Rule adopted |
|---|---|---|
| `Marine Systems (BS)` | substring search for "MS" matches inside "Systems" | parse the **credential field** (the last parenthesised group) and match **whole tokens**, case-sensitively |
| `Asia Minor Studies (BA)` | contains "Minor" → wrongly excluded as a minor | apply minor patterns only to the **credential-stripped** base title |
| `Chemistry (BS/MS)` | looks like a bachelor's | scan **all** credential groups; if both undergrad and graduate tokens appear → excluded as combined |
| `Interdisciplinary Studies` | no credential at all | never guess — route to `manual_review.csv` |

**Design rule:** every exclusion is written to a CSV **with its reason and the
evidence**. Nothing is silently dropped. A human can audit any decision.

### Problem 4 — Finding the content inside the page (this caused the incident)

USC's pages are built from nested HTML *layout* tables — the site header, nav,
toolbar and programme content are all `<td>`s. So "extract the main content" has
no obvious answer.

The original approach: score every plausible container and take the highest.
Score was dominated by `log(text_length) × 12` — more text, higher score.

**Why that is a landmine:** the whole `<body>` always contains the most text. On
a programme whose content is *short relative to the page furniture*, the body
wins. On "Environmental Science and Health (BA)" the whole body beat the correct
content region **305.0 to 304.7 — a 0.3-point margin.** The output then contained
the site header, the skip-link, and a literal `<script>` tag, with the programme
blurb duplicated 8× by table colspan expansion.

**Design rule that replaced it:** the container is a **structural requirement,
not a competition.** For a programme page only a real content region is eligible;
the whole document is ineligible *at any score*. If no content region exists,
raise an error — never silently degrade.

---

## 3. Architecture: the pipeline

```
year choice
  → catalogue_resolver.py   year → catoid → navoid (three first-party proofs)
  → acquisition.py          layered fetch + semantic validation + WAF handling
  → boundary.py             find the programme-list section
  → discovery.py            collect + canonicalise programme links
  → classification.py       include / exclude / manual-review, with evidence
  → extraction.py           choose the content region   ← incident lived here
  → text_renderer.py        HTML → deterministic plain text
  → output_validation.py    validate the FINAL TEXT     ← the missing gate
  → output.py               atomic write + stable filenames
  → state.py                SQLite: per-programme commit, SHA-256, resume
  → audit.py                verify hashes/counts/indexes, regenerate reports
```

Two things worth internalising:

**(a) Every stage records evidence, not just results.** The chosen container, the
score, the runner-up, the acquisition mode, the validation reasons — all persisted.
That is *why* the incident was diagnosable months later from CSVs alone.

**(b) State lives in SQLite, committed per programme.** So a run can be killed at
any moment and resumed. Filenames and sequence numbers are stable across runs
because they are reserved in the database, not recomputed.

---

## 4. The incident, as a lesson in debugging method

This is the most transferable part of the project.

**Symptom:** one file (`107 Environmental Science`) contained navigation instead
of programme content.

The temptation is to look at page 107 and patch whatever looks wrong. What we did
instead:

**Step 1 — Get a control.** File 106, from the same run, was perfect. Two files,
same code, same run, opposite outcomes. That pair is worth more than any amount
of staring at 107.

**Step 2 — Read the recorded evidence before touching code.** `fetch_log.csv`
showed 107 was accepted on **HTTP 202** (the WAF challenge status) after 63s in
the browser. First hypothesis: the WAF corrupted the capture.

**Step 3 — Test the hypothesis against the whole corpus, not the one file.**
Audited all 470 outputs for the exact literal strings found in 107
(`Skip to Navigation`, `| University of Southern California`, `Begin Responsive`,
`<script`). Result: **158 of 470 files (34%) were contaminated** — and 145 of them
came from clean HTTP **200** responses. **The WAF hypothesis was dead.** Runtime
analysis killed a second hypothesis: contaminated pages had a *median 7s* runtime
versus 6s for clean ones, and the four slowest pages (up to 962s) were all fine.

**Step 4 — Reproduce deterministically, offline.** Fetched the 107 page, saved the
HTML, and ran the real `select_main_container()` on it while printing every
candidate's score. Out came `body 305.0` vs `td.block_content 304.7`. Root cause
proven, reproducible without the network, in under a second.

**Step 5 — Verify the fix produces *correct* content, not merely different
content.** Extracting the correct region from that same saved HTML yielded the
full programme with all courses and `Total units: 52`.

**The method, generalised:**
1. find a control case that works
2. read the evidence the system already recorded
3. form a hypothesis, then try hard to *kill* it with corpus-wide data
4. reproduce offline and deterministically
5. prove the fix restores correct output, then re-audit everything

**What made the bug survive so long: every check was upstream of the mistake.**
Acquisition proved the right *page* arrived. Nothing proved the right *part* of it
was extracted. The only text-level gate was `len(text) > 200`. So 4,614 characters
of navigation was written with `Extraction Status: complete`, and the run reported
"207/207 successful, 0 failed."

> **Lesson to carry everywhere: validate your output, not just your input.**

---

## 5. How validation is designed (and how it went wrong twice)

The new gate (`output_validation.py`) checks the text that is *about to be
written*:

- no contamination fingerprints (taken verbatim from the real broken files)
- the body opens with **its own programme title** as a heading
- course/unit content **or** real catalogue section structure
- no sentence repeated 3+ times (the colspan-duplication signature)
- a 200-character floor as a backstop

**Two false positives we caused and had to fix — this is the important bit:**

1. We first treated a bare `Row 1:` label as fatal. But the renderer legitimately
   emits `Row 1:` for **real course tables**. The true fingerprint is the *site
   header inside* such a row. Over-broad rules destroy good data.
2. We first required course codes. Then the run refused
   `Interdisciplinary Studies (BA)` — a self-designed major that has **no course
   list by design** — and two minors that are ~300-character pointers ("See
   complete description in the USC Price School section"). We fetched all three
   live to establish ground truth, then widened the rules with tests.

**Every threshold is derived from the corpus, never invented:**
- smallest *clean* body observed = 971 chars → so the hard floor is 200, five times
  lower, and length alone never rejects a body that shows semantic evidence
- max repeated sentence across 470 clean files = 2 → threshold of 3 has real
  headroom, and broken 107 sat at 8

> **Lesson: a validation rule with no corpus measurement behind it is a guess,
> and guesses cut both ways — false positives destroy good data as surely as
> false negatives let bad data through.**

---

## 6. How it is tested

**211 tests.** The structure matters more than the count:

| Layer | What it pins | Example |
|---|---|---|
| Unit | pure functions | credential parsing: `Marine Systems (BS)` must not match "MS" |
| Fixture | HTML → text, using **real saved pages** | the actual 107 page must extract cleanly; the actual 106 must be unchanged |
| Adversarial regression | every bug ever found, so it cannot return | 16 from the first review + 5 from the incident + 3 from self-review |
| Integration | real Chromium against a localhost fixture site | JS-shell escalation, challenge hand-off, accordion expansion |
| End-to-end | resume, interruption, tamper repair across separate processes | kill mid-run, rerun, verify no duplicates and no re-downloads |

**Two testing principles worth stealing:**

1. **Fixtures are real captured pages, not hand-written HTML.** `tests/fixtures/
   program_107_...html` is the actual page that broke. Hand-written HTML tests
   what you *imagine* the site looks like — which is exactly the assumption that
   was wrong.
2. **Write the test that documents the defect, not only the fix.** There is a
   test asserting that *without* the guard, the body still wins on page 107. If
   someone removes the guard, that test tells them precisely what they re-broke.

**Adversarial testing.** We wrote 11 attack fixtures trying to *defeat* the fix:
chrome hidden inside a whitelisted region, a clean region behind an unknown
selector, renamed classes, tied candidates, empty regions, malformed HTML, a
legitimate table containing "Row 1". Two attacks succeeded and produced real
fixes. **Two "successes" turned out to be flaws in my own test oracle** — one
fixture was smaller than the 200-char floor, and one flagged legitimate table
output as contamination. Always ask whether a failing test is finding a product
bug or a test bug.

---

## 7. How to rebuild this from scratch

Ordered so that each step is verifiable before the next.

1. **Resolve the catalogue.** Fetch the archive list, pick the non-archived
   edition, corroborate the year on its own home page, get the Programs navoid
   from the site's navigation. *Verify: prints the expected year and URL.*
2. **Build the layered fetcher.** Plain HTTP with realistic headers → alternate
   representation → headless browser. Add semantic validation **first**, so
   "success" is meaningful from day one. Treat `x-amzn-waf-action` and a 202 as a
   challenge. Re-sync browser cookies to the HTTP client after every browser win.
   *Verify: log the acquisition mode per request; you should see plain HTTP
   succeeding most of the time.*
3. **Discover the programme links.** Bound discovery to the programme list; keep
   every link with its title.
4. **Classify with evidence.** Token-aware credential parsing. Write
   `excluded_programs.csv` and `manual_review.csv` before you write any programme
   file — the counts tell you instantly whether classification is sane
   (expect ~470 included, ~623 excluded, ~57 manual review for 2026-27).
5. **Select the content region STRUCTURALLY.** Only a real content container is
   eligible. Never the whole document. Raise an error rather than degrade.
   *Verify: assert the chosen container on a saved page snapshot.*
6. **Render deterministically.** Headings, nested lists, real tables, footnotes.
   Distinguish **layout** tables (single-column / presentation → unwrap) from
   **data** tables (keep). *Verify: same HTML in → byte-identical text out, every
   time.*
7. **Validate the output text before writing.** Fingerprints, own-title heading,
   course/unit or section evidence, duplication, floor. *Verify: feed it the known
   broken file — it must reject with reasons.*
8. **Write atomically, record state in SQLite,** hash every file.
9. **Make resume re-validate, not just re-hash.** A matching hash proves the file
   is *unmodified*, not that it is *correct*.
10. **Audit the corpus with the same validator production uses** — import it, do
    not reimplement it, or your audit and your scraper will disagree.

---

## 8. Seven principles this project taught

1. **Validate outputs, not just inputs.** The bug survived because every check
   was upstream of the mistake.
2. **A hash proves integrity, not correctness.** 158 files had perfect hashes.
3. **Never let a fallback compete on score with the real answer.** Make it
   structurally ineligible.
4. **Fail loudly and write nothing** rather than write something plausible.
5. **Derive thresholds from measurement.** Then state the measurement in the code
   comment, so the next person can re-check it.
6. **Keep evidence per decision.** It is what makes a defect diagnosable later.
7. **Try to kill your own hypothesis.** The first two explanations here (WAF,
   JavaScript timing) were both wrong and both plausible; corpus data killed them
   in minutes.
