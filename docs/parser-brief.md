# STARS parser — scope, ownership, and how to build it

_Vishal Gupta, with Claude support. Written for @Abhi and @Agastya as they pick up the parser; section 12 is addressed to @Tanzil._

Hi @Abhi @Agastya — here's where the STARS parser stands and how I'd like us to approach it. Abhi, this is your on-ramp; Agastya, it should line up with what you've already been finding.

It's long on purpose. If you hand parts of it to Claude while implementing, there's enough detail here for it to work from — but it's also written to be read and argued with. If something here doesn't match what you see in a real report, the report wins. Come tell me.

---

## 1. Coordination — before more code gets written

You've both been looking at the parser. Agastya, could you push what you have to a branch this week, even if it's rough? Not to be judged — just so we can see it before anyone builds further and nobody's work gets thrown away.

My proposal, open to discussion: **Abhi owns `stars-parser/`**, as a module with a single owner. Agastya, if your branch is ahead of `main`, it becomes the starting point rather than being discarded. You'd stay owner of `catalog/` (the Schedule of Classes scrape) and review Abhi's parser PRs — Abhi is new to this report format and would benefit from a reviewer who's already stared at these files.

Two people editing one module is the blocker, not the fix. One owner, one reviewer.

---

## 2. Read this first

`docs/reference/01-reading-a-stars-report.md` in the repo — how a STARS report is actually laid out. It's new. It exists because most parser bugs turn out to be misunderstandings of the report rather than of the code. `docs/reference/02-usc-degree-requirements.md` has the underlying USC rules if you want more depth.

---

## 3. Scope — narrower than what's in the repo now

Support **only** the single-column PDF a student gets by doing print-to-PDF from `experience.usc.edu`.

Explicitly out of scope — please delete rather than maintain:

- **OCR / Tesseract.** OCR means optical character recognition — reading text out of an image. You need it when a PDF is a scan, i.e. a picture of a page with no selectable text. Our target export has a real text layer, so text can be pulled out directly. The OCR fallback is a heavy dependency guarding a case that no longer comes up.
- **The two-column layout.** Some STARS variants print in two columns side by side, and extracting text from those interleaves the columns into nonsense. Only the Registrar uses those; students never see them.
- **Reports from other USC systems.** Several systems around USC show STARS data with slightly different formatting. The current README says this parser was built for PDFs from `my.usc.edu`, which is a different source — please update that.

Narrow and correct beats broad and unreliable.

---

## 4. The bug Agastya found, and what's underneath it

Agastya found that the parser doesn't pull the GPA out of uploaded reports. I dug into why, and it turns out to explain a lot more than the GPA.

The cause is in `textExtract.js`. It currently does this:

```js
const pageText = content.items.map((item) => item.str).join(" ");
```

A PDF doesn't store lines of text. It stores fragments, each with x/y coordinates on the page. That line takes all the fragments and joins them with spaces — so an entire page becomes **one enormous line**. Every pattern in `fieldParser.js` that expects to work line by line then has nothing to work with.

Running the current code against a real report, versus the same code after rebuilding lines properly:

```
                       current    after fix
major                  MISSING    ok
classLevel             MISSING    ok
catalogYear            MISSING    ok
upperDivisionGpa       MISSING    ok
completed courses        0          52
```

Zero courses. The course-row pattern needs to match at the start of a line, and there are no line starts left. So this one bug accounts for most of what's broken — and it's in the twenty lines that read the PDF, not in the several hundred that parse it.

Section 5 is the fix.

---

## 5. Architecture — my strong suggestion

**Keep the whole parser in JavaScript.** It's where the code already is, it runs client-side where the student's file already is, and it's the language you're both comfortable in. If you have a better idea, I'm genuinely open — but this is my recommendation and I'd rather you spend your effort on the parsing itself.

**Rebuild lines from the PDF before doing anything else.** Group text fragments by their vertical position, sort each group left to right, and join. About ten lines:

```js
const content = await page.getTextContent();
const lines = new Map();
for (const item of content.items) {
  const y = item.transform[5];              // vertical position of the text baseline
  if (!lines.has(y)) lines.set(y, []);
  lines.get(y).push(item);
}
const text = [...lines.entries()]
  .sort((a, b) => b[0] - a[0])              // top of the page downwards
  .map(([, items]) => items
    .sort((a, b) => a.transform[4] - b.transform[4])   // left to right
    .map(i => i.str).join(""))
  .join("\n");
```

Grouping on the exact baseline value is enough — fragments on the same visual line share it. I've checked this against every real report we hold and it reproduces them correctly.

**Sanity check before writing any parsing logic.** Extract one report, print the text, and count the lines. You should get roughly 350 or more non-empty lines, with course rows that look like course rows. If you get 7 lines, that's one per page and line rebuilding isn't working yet. Fix that first — everything downstream depends on it, and it's far easier to debug on its own.

**Keep the two stages as separate functions.** PDF-to-text, then text-to-structured-data, with plain text passing between them. That way you can test the parsing from a terminal against a saved `.txt` file, with no browser and no PDF involved — which removes most of the debugging pain, and there will be debugging pain.

---

## 6. What to output

`validator/README.md` documents what the next-semester validator reads. It's five things: `major`, `classLevel`, `gpa`, `completedCourses` and `inProgressCourses`.

That's the minimum. Natalie and Francis are about to start the four-year degree planner, though, and it needs more detail per course — so please capture the following on every course row while you're already there. Adding it now is nearly free; going back for it later means redoing this work.

For each course:

- **`term`** — the five-digit term code from the row, e.g. `20253`. It's the year plus a term digit, where 1 = spring, 2 = summer, 3 = fall. So `20243` is fall 2024 and `20251` is spring 2025. Keep the raw code, don't convert it to a date.
- **`code`** — the course code, e.g. `ESRM 150`.
- **`grade`** — the grade string exactly as printed. Don't assume it's always a letter.
- **`units`** — the unit value from the row.
- **`source`** — where the credit came from: `usc`, `transfer_specific`, or `transfer_generic`. Section 7 explains the difference.

Keep the two lists the validator expects — `completedCourses` and `inProgressCourses` — and just add these keys to each entry. The validator reads `.code` and `.grade` and ignores anything else, so this won't break it. Its existing test fixture already carries `term` and `units`, so `source` is the only genuinely new field.

**Why the planner needs the term.** A four-year plan has to know not just what a student has taken but when — so it can sequence future semesters with prerequisites landing before the courses that need them, tell completed work from in-progress work, and reason term by term instead of treating everything as one undifferentiated pile.

This is a minimal **output**, not a minimal **implementation** — see section 8 on how to get there.

---

## 7. Transfer credit — the part most likely to bite you

Neither of you has had reason to learn USC's transfer rules, so here's the background, because it drives a real decision in the code.

When a student transfers credit in from another institution, USC does one of two things with it.

**Case one: it maps the course to a specific USC equivalent.** USC decides your community-college statistics course is equivalent to `ESRM 150`. On the report it appears under that USC course code, with `TR` in the grade column instead of a letter. As far as the degree is concerned, the student has taken ESRM 150.

**Case two: it accepts the work as generic credit with no USC equivalent.** The student gets units, but USC hasn't decided the work equals any particular USC course. These appear as placeholder rows named things like `TR-PSYC`, `TR-COMP-1`, `TR-NUTRITION`. That isn't a course code — it's a label meaning "some psychology credit".

Why the distinction matters:

- **Both count toward the 128-unit graduation total.** Neither is wasted.
- **Only case one can satisfy a prerequisite.** If CSCI 201 requires CSCI 104, having `TR-COMP-1` on your record doesn't clear it, because USC never said that transfer course was CSCI 104. If the transfer came in **as** CSCI 104, it does.
- **Only case one can fill a named degree requirement.** Generic credit counts as free elective units. This matters a lot for the degree planner — treating generic credit as able to fill requirements would understate how much a student has left to do.

**What this means for the code.** The danger isn't logic, it's hygiene. `TR-COMP-1` doesn't look like a course code, so there are two tempting mistakes:

- **Dropping the row** because it doesn't match your course-code pattern. That undercounts the student's units and loses credit they actually earned.
- **Cleaning it up** into something that does look like a code — stripping the `TR-`, or reshaping it into `COMP 1`. That's worse, because it could match a prerequisite it doesn't satisfy, and now you're telling a student they can register for something they can't.

**Pass these rows through unchanged** and tag them `source: "transfer_generic"`. Tag a transfer that arrived under a real USC code as `source: "transfer_specific"` — you can spot those by the `TR` in the grade column. Everything else is `source: "usc"`.

**Where transfer credit actually appears.** There's no single "transfer credit" list. It shows up in up to three places, meaning different things:

1. **A summary line near the top,** looking like `99993 TRNSFR WORK 28.0 TR — Total Transfer Units`. It sits among the course rows and looks like one, but it's a **total**. `99993` isn't a real term and `TRNSFR WORK` isn't a real course. Parse it as a course and you add the student's whole transfer balance a second time.
2. **Inside a requirement block,** where a transferred course was applied to a specific requirement.
3. **Under "other courses in your academic account",** for transferred work not applied to any requirement.

An individual transfer appears in 2 **or** 3, never both — so the real transfer courses are the union of those two, and item 1 is just their total. Since you shouldn't be harvesting courses out of requirement blocks anyway (section 9), most transfers you collect will come from "other courses". That summary line is still useful though: the transfer units you collected should add up to it, and if they don't you've missed some.

---

## 8. Finding your way around the report

The obvious approach is one pattern per field, each scanning the whole document. That works until two parts of the report contain similar-looking text, and then it fails quietly.

What I'd like instead is a cheap pass up front that cuts the document into labelled chunks, so your field patterns only ever run against the chunk they belong to.

**Step one: throw away what isn't the report.** Skip everything before the first `PREPARED:` or `PROGRAM:` line — that's the print preamble, holding the student's name and ID and nothing useful. Then strip the repeating page header and footer, which appear at every page break and can land in the middle of a block and split it in half.

**Step two: split on the divider rows.** The report separates blocks with long runs of underscores, and frames a few banners with runs of asterisks. In a typical report there are around 27 underscore dividers and a handful of asterisk ones. These are real and you can rely on them — but note they separate **blocks**, which are finer-grained than sections. One section can contain several.

**Step three: label each chunk by distinctive words inside it,** not by its position. The chunk containing both `64` and `RESIDEN` is the residence requirement; the one containing `NCAA` is the athletics section; the one containing `OTHER COURSES` is the unapplied-coursework list.

**This is the important part: not every report has every section.** A student with no minor has no minor block. A student who isn't an athlete has no NCAA section. In the report I checked while writing this, `NCAA` appears zero times. So never count blocks, never assume a fixed order, and always handle "this section is absent" as a normal case rather than an error. Completion status changes things too — a satisfied requirement collapses to a single line while an unsatisfied one expands to show what's missing, so the same section varies in size between students.

A few specific traps worth knowing:

- **`major` comes from the header `PROGRAM` line, not the `CURRENT POST` row.** On a second-major report, current post shows the student's **primary** post, so you'd silently report the wrong major.
- **Numbered sub-requirements skip unused numbers** and can jump from `1)` to `3)`. Don't assume a dense sequence.
- **Course titles are truncated** to a fixed width, so they can't be matched on. The course code is the reliable key.

Chunking first is maybe an hour of work and it prevents three bugs I know are waiting: course rows inside requirement blocks being counted as coursework when they're repeats, the NCAA section inflating the course list, and `major` coming from the wrong place. All three are "right pattern, wrong part of the document" errors. As a bonus, when Natalie and Francis need the requirement blocks for the degree planner, they're already sitting there labelled.

---

## 9. Building the course list correctly

This isn't polish — it's what makes the five required fields right in the first place.

- Combine the master course list with "other courses in your academic account", then remove duplicates by (term, course). A course can legitimately appear in both — physical education commonly does.
- **Never collect courses from inside requirement blocks.** Those repeat courses already in the master list, so you'd count them twice.
- Detect the NCAA section and skip it. It re-lists coursework and is an athletics-eligibility audit, not a degree audit.
- A row carrying `RG` or `>IP` is **in progress**, not completed — those units aren't earned yet. They include registrations for future terms.
- Preserve the grade string exactly as printed.

---

## 10. Fail loudly

A parser that returns nothing is much safer than one that returns a plausible-looking subset.

If an expected landmark is missing, raise an error naming it. Don't return a partial object. If `completedCourses` comes back empty, the validator can't tell that from a student who has genuinely taken nothing, and it'll happily approve a schedule full of courses they aren't eligible for. That's exactly the failure mode the current code has today.

A good self-check: the units implied by your course list should reconcile with the report's own earned-units total. If they don't, something was missed, and it's better to say so than to guess.

---

## 11. Sample reports worth testing against

A straightforward single-major student; a transfer student with both kinds of transfer credit; a student with a minor; someone with in-progress and future-term registrations; an athlete, to prove the NCAA section gets skipped; and a second-major report, to prove `major` comes from the header rather than current post.

Redacted only — never commit a report with real student data. We have some examples in the Hugging Face dataset, and should get more once the collection tool is deployed.

Worth knowing the ten fixtures currently in `stars-parser/test/fixtures` are OCR output from scanned two-column reports — the format we just put out of scope. They'll need replacing.

---

## 12. Testing — and an ask for @Tanzil

Tanzil, pulling you in because this part crosses the parser/validator boundary and you own the validator side.

**Testing the parser, in JavaScript.** Node has a test runner built in — `node --test`, with `node:test` and `node:assert`. No Jest, no Babel, no config, no install. If you've heard JavaScript testing is a nightmare of tooling, that's what people mean, and you can skip the whole category. The parsing logic is about the easiest kind of code to test: text in, object out. No mocking, no browser, no async.

**One thing to fix before trusting the tests that exist.** `stars-parser/test/parser.test.js` imports only `fs` and `path` — it re-implements the extraction functions **inside the test file** instead of importing them from `fieldParser.js`. So it tests a copy of the code. `fieldParser.js` could break completely and the suite would still pass. Please wire the tests to the real module first; a green suite that proves nothing is worse than no suite.

**Testing the validator, in Python.** Already done and already the right shape — `validator/test/fixtures/mock_stars_report.json` is loaded with `json.loads(...)` and passed straight into `validate_next_semester()`. Nothing to build.

**The gap worth closing.** Each suite proves its own module is internally consistent. Neither proves the two agree with each other. The validator's STARS fixture is hand-written, and nothing checks it against what the parser actually produces. That seam is where this will break.

The proposal is to **make them the same file**. For each redacted sample, commit two files side by side:

```
fixtures/stars/<name>.txt     <- extracted text; the parser's input
fixtures/stars/<name>.json    <- the parser's expected output AND the validator's input
```

The JavaScript parser test asserts that parsing `<name>.txt` equals `<name>.json`. The Python validator test loads `<name>.json` as its `stars_summary`. Same bytes, both sides.

Two things follow. A parser change that alters the output shape breaks a Python test immediately, instead of surfacing as a broken app in a browser three weeks later. And adding one new sample student exercises both modules at once.

**Tanzil — the ask:** are you happy pointing the validator's fixtures at a shared directory rather than `validator/test/fixtures/`? And should `mock_stars_report.json` become one of these shared files, or stay as a separate hand-built case? My instinct is to keep at least one hand-written stub for edge cases the real samples don't happen to cover, but you know that suite better than I do.

---

Shout if any of this doesn't match what you're seeing. The reference docs are new and were reconstructed from a limited set of samples — a real report always wins over our description of one.
