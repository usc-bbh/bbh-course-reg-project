# Catalogue Requirement Classifier — Brief (Natalie)

_Written 2026-08-17. Vishal is away until 2026-08-24 and will be slow to respond.
Everything you need to start is in this file, including the decisions you'd otherwise
have to ask about._

---

## Where this is going

Francis has scraped all 470 USC undergraduate programmes from the catalogue into plain text
files. We want to turn that pile of English prose into a machine-readable JSON file of degree
requirements, using an LLM to absorb the fact that the catalogue is wildly inconsistent in
how it words the same requirement.

You've already done the hard intellectual work — the taxonomy in
`constraint_classifier_prompt.md` §6. There are two jobs left, and you can work on them in
either order.

**Nobody expects both to be finished in a week.** They're structured so that partial progress
on either one is still useful, and so that someone else can pick up a piece if you get stuck.

---

# Job 1 — The taxonomy, as its own document

This is the document we asked for back in July and never got. It should be a standalone
markdown file — **just the taxonomy**, none of the parsing instructions. Call it
`constraint_taxonomy.md`.

One section per constraint family. Each section has four parts, in this order:

1. **A name a human can understand.** Not a code. "Course count with a filter" beats
   `NOT_CNS_XREQ_EXTERNAL_UNIT_CAP`.
2. **A description in plain English.** Two or three sentences: what kind of requirement this
   is and what makes it different from the others.
3. **A JSON schema** for encoding a requirement of this family.
4. **Examples from the catalogue** — real sentences, quoted, each followed by what that
   sentence looks like once encoded in the schema from part 3.

### If part 3 is blocking you, skip it

If you get stuck on the JSON schemas and can't reach Vishal, **write the file without them.**
Name, description, and examples for each family is genuinely most of the value, and Job 2
doesn't need the schemas to get started. A finished document with three of four parts beats a
half-finished document with all four. Come back to the schemas after.

### Two decisions already made, so you don't have to ask

**Drop `solver_role` and `validator_role`.** They describe what a solver would do with each
constraint — but we aren't building anything that generates a schedule yet, and we're a long
way from it. For now we only need to capture what the catalogue *says*. Taking those out will
also simplify the schema work considerably.

**Aim for around five families, not fifty.** The current taxonomy has a lot of subtypes, and a
lot of them are the same requirement wearing different words. Here's a test you can apply
mechanically instead of by feel:

> **Two types are the same family if you'd fill in the same blanks to describe them.**
> If the only difference is the wording the catalogue happened to use, that's one family, not two.

Worked example — these are currently four separate subtypes:

- *"At least 8 units must be from the Department of History course offerings."*
- *"No more than two total courses in the major may be taken outside the college."*
- *"No more than 2 of the 9 required courses may be at the 100/200 level."*
- *"Students must choose at least four classes outside their major department."*

| blank | History | outside college | 100/200 level | outside dept |
|---|---|---|---|---|
| which courses count | HIST prefix | not in Dornsife | level ≤ 299 | not in major dept |
| counting what | units | courses | courses | courses |
| the bound | at least 8 | at most 2 | at most 2 | at least 4 |

Same three blanks every time, different values. **That's one family, not four** — and one JSON
schema instead of four.

The guard against going too far the other way: two things are only the same family if the
software would also *handle* them the same way. A requirement you check by counting, and a
requirement where an adviser decides case by case, stay separate no matter how similarly
they're worded.

This is the same conclusion as the review of your July `.docx` — that the ~33 types were
really one reusable pattern with a filter, a measure, and a threshold. That feedback stalled
partway through and never reached you. That's on our end, not yours.

### The part of the schema you can write right now

Some fields are on **every** record regardless of family. You can design that part today
without having settled a single family:

```json
{
  "id": "CS-BS-01",
  "family": "<name of the family>",
  "source_text": "<the exact sentence from the catalogue, copied verbatim>",
  "description": "<one plain sentence saying what this requires>",
  "details": { }
}
```

`details` is the only part that changes per family. Everything above it is fixed. So the
per-family work is just: **what goes inside `details` for this family?** That's a much smaller
question than "design a JSON schema", and it's a good place to start.

---

# Job 2 — The pipeline

A Python program that reads Francis's scraped files, sends each one to Claude along with the
taxonomy, and writes out JSON.

**This doesn't depend on Job 1 being finished.** Start it with whatever version of the
taxonomy exists. A rough taxonomy through a working pipeline teaches you more about the
taxonomy than staring at the taxonomy does.

## Four files, four jobs

Keep these separate. It's tempting to write one big script; don't. Separate files mean you can
fix one part without breaking the others, and someone else can take over a piece.

### 1. `prompt_v1.md` — the instructions

Already written for you, in this folder. It has three placeholders (`{{PROGRAM_NAME}}`,
`{{TAXONOMY}}`, `{{REQUIREMENTS}}`) that the Python fills in.

**Expect to rewrite parts of it.** That's the job, not a sign something's wrong. Tuning advice
is at the bottom of this brief.

### 2. `constraint_taxonomy.md` — the taxonomy

Job 1's output. The Python reads it as plain text and pastes it into the prompt. Whatever
state it's in, that's what gets used.

### 3. `run_classifier.py` — makes the calls

Roughly:

```
for each .txt file in the programmes folder:
    if we already have output for it: skip
    read the file
    build the prompt: prompt template + taxonomy + this file's text
    call the Claude API
    save the raw response to out/<name>.response.txt
    try to parse it as JSON
        if it parses:      save to out/<name>.json
        if it doesn't:     record the failure and move on — do not crash
```

Six things to get right, each of which will save you an afternoon:

**Save the raw response before you parse it.** `out/<name>.response.txt` is exactly what came
back from the model, untouched. If the JSON is malformed, that file is how you find out why.
Without it you just have an error and no evidence. (This is a *different* thing from Francis's
input `.txt` files — that's the catalogue text going in, this is the model's answer coming
back.)

**Skip files you've already done.** One `if` at the top of the loop. It means you can stop and
restart without re-paying for work, which you will do many times.

**Separate "call once" from "loop over everything."** Write a function that takes one
programme's text and returns the raw response. The loop just calls it in turn. Then you can
test on a single file before spending anything, and debugging one bad case is easy.

**Never let one bad file kill the run.** Wrap each iteration so a failure gets recorded and
the loop keeps going. Coming back to a run that died on file 3 of 15 is miserable.

**Stamp every output.** Put the model name, the date, and which prompt version you used at the
top of each JSON. Next year someone re-runs this against a new catalogue and will need to know
what produced what.

**Set temperature to 0.** You want the same input to give the same output while you're tuning.

### 4. `check_results.py` — grades the output

A **separate** script that reads the `out/` folder and reports. Keeping it separate means you
can re-check every result instantly and for free, without re-running any API calls. You'll run
this far more often than the classifier.

Three checks per programme:

1. Is the file valid JSON at all?
2. Does every constraint name a family that actually exists in the taxonomy, and quote its
   source text?
3. Did the model report anything in `unclassified`?

Then one summary CSV, one row per programme:

| program | parsed | constraints found | count per family | unclassified count | status |
|---|---|---|---|---|---|

**That CSV is the thing Vishal reads when he's back.** It's what tells us whether the taxonomy
actually covers the catalogue, which was the original question behind all of this. It also
works fine before the per-family schemas exist — none of the three checks need them.

---

## Your test set — use these 15 files, not all 470

Running the whole catalogue with an untuned prompt wastes money and teaches you nothing. These
fifteen were picked to break the prompt in different ways. If it handles all fifteen, it'll
handle most of the rest.

| file | why it's here |
|---|---|
| `025_astronomy_ba.txt` | tiny, minimal structure — start here |
| `102_economics_ba.txt` | one prose paragraph containing six separate requirements |
| `086_computer_science_bs.txt` | headings + bullets, plus grade rules and a "any 300/400-level CSCI" pool |
| `141_journalism_ba.txt` | clean structure, plus electives that just say "consult an adviser" |
| `120_global_health_studies_bs.txt` | deeply nested; unit counts live in headings; `or` chains |
| `162_occupational_therapy_bs.txt` | "A or B or C **with** D" — nested and/or logic |
| `192_social_work_bsw.txt` | 440 hours of fieldwork — a requirement measured in hours |
| `183_public_policy_bs.txt` | "choose one of these tracks" — alternative requirement sets |
| `134_interdisciplinary_studies_ba.txt` | almost entirely adviser-determined; no course lists |
| `042_business_administration_bs.txt` | electives defined by prefix and level, not by a list |
| `124_history_ba.txt` | the largest file in the corpus |
| `079_cognitive_science_ba.txt` | "may not take more than one of these overlapping courses" |
| `458_statistics_minor.txt` | a minor, which has different policy rules than a major |
| `399_natural_science_minor.txt` | "not available to majors in the natural sciences" |
| `169_performance_violin_viola_violoncello_double_bass_or_bm.txt` | "required each semester in residence" |

Fifteen files costs a few cents per run. Run them as often as you like.

---

## API key

Vishal is setting up a Claude API key with a hard $50 spending cap. It'll come to you by DM.

- Put it in a file called `.env` in the project folder: `ANTHROPIC_API_KEY=sk-ant-...`
- Add `.env` to `.gitignore` **before** your first commit.
- **Never paste the key into a `.py` file.** If it ever lands in a commit it has to be revoked
  and reissued.
- Fifteen files is pennies. All 470 is roughly $20–40 — don't do that run without checking in.

---

## Tuning the prompt

You will not get good output on the first try. Normal. The loop is:

1. Run the 15 files.
2. Run `check_results.py`.
3. Open the worst result and read `out/<name>.response.txt` — the model's actual words.
4. Change **one** thing in the prompt.
5. Run again.

Change one thing at a time. If you change three and it gets better, you don't know which one
helped, and you'll re-break it later.

Common failure modes and what usually fixes them:

| symptom | usual fix |
|---|---|
| Output isn't valid JSON | Restate "return only JSON, no prose, no code fence" at the *end* of the prompt. Last instruction wins. |
| Made-up family names | Say "the `family` field must be copied exactly from the taxonomy" and list the legal names right there in the prompt. |
| `source_text` is paraphrased, not quoted | Add "copy the text character for character; do not summarise" plus one right example and one wrong example. |
| Whole requirements missing | The model is skipping awkward ones. Ask it to work through the document top to bottom and account for every section heading. |
| `unclassified` always empty on hard programmes | It's forcing bad fits. Say explicitly that an empty `unclassified` list on a complicated programme is a mistake. |
| Contact info and faculty names showing up as requirements | Add them to the "these are not requirements" list. |

Keep the old versions. `prompt_v1.md`, `prompt_v2.md`, and so on — when v4 is worse than v2
you want to be able to look.

---

## Definition of done

You will not finish all of this in a week. In rough priority order:

1. `constraint_taxonomy.md` exists, with names, descriptions and examples for each family.
   (Schemas optional — see above.)
2. `run_classifier.py` works on **one** file end to end.
3. It runs across all fifteen test files without crashing.
4. `check_results.py` produces the summary CSV.
5. A couple of rounds of prompt tuning, with the versions kept.

Getting to 2 is a real week's work if the setup fights you. Getting to 4 is a good week.

---

## When you're stuck

Post in the channel — Tanzil and Francis can both help with the Python. Claude can help with
all of it; paste this file in at the start of a session so it knows the context.

And keep a running list of anything you weren't sure about — a judgment call you made, a
requirement that didn't fit anywhere, a question you'd have asked if Vishal were around. Put
it in `taxonomy_open_questions.md`. That file is the agenda for the first meeting when he's
back, and it's a deliverable in its own right — don't sit blocked on a question when you can
write it down and keep moving.
