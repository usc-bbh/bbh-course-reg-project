# Taxonomy rewrite: plan and check

_Response to `FEEDBACK_phase1.md`, covering T1, T3–T8 and T11–T13. Written 2026-10-13._

**Where things stand.** I've mapped every example in the current `constraint_taxonomy.md` to its
new encoding (below), drafted the outline for the rewrite, and built a check that runs on every
edit. I'll do the rewrite itself next. Questions and decisions are in
[`taxonomy_open_questions.md`](taxonomy_open_questions.md).

## The check

```bash
python check_taxonomy.py                 # every JSON example in constraint_taxonomy.md
python check_taxonomy.py --dir examples  # your five programs
python -m unittest test_taxonomy         # tests for the check and for is_eligible
```

Every JSON example in the taxonomy is checked in four ways:

1. **The schema.** It must validate against `requirement_schema.json`. The block's kind (node,
   `of_which` check, `unclassified` entry or whole program) is worked out from its shape, so the
   taxonomy needs no extra markup that the model would see.
2. **Old vocabulary.** These fail the check: `filter`, `pool`, `pool_rule`, `bound`, `measure`,
   `scope`, `fixed`, `source_text`, the old family names, and `"..."` placeholders.
3. **`eq` needs "exactly".** Every `"op": "eq"` must have "exactly" in the `>` catalogue quote
   above it (T5).
4. **Code can evaluate it.** Every `eligible_if` must run through `is_eligible` (T2, in
   `eligibility.py`) and return True, False or `"unknown"`.

**Baseline today: 0 of 31 taxonomy examples pass. Target: all pass.** Your five `examples/` pass,
and the tests include deliberately broken cases (`"treshold"`, a free-text `eligible_if`, a bad
course code three levels down) that fail with a readable path. Placeholder leaves (`course_reuse`,
`sequencing`, `manual_review`) are only warned about for old keys inside their `details`, since
section 2.3 says not to polish them yet.

## Golden cases: checking meaning, not just shape (proof of concept)

The schema check can't tell `min 3` from `min 4`. So `bip.py` turns a program's JSON into a binary
integer program (PuLP): a yes/no variable for each course in each slot, plus constraints for the
thresholds, `all_of` / `choose`, the one-slot rule and `of_which`. It then does two things:

- **Audit.** Every requirement in the JSON is listed as converted, "needs data" (`unresolved`,
  `school`) or LOST (placeholder families, or a key the converter doesn't read), so no
  constraint is dropped silently. Economics and Religion convert completely. Public Policy loses
  only its two `manual_review` placeholders, and its three `unresolved` pools are marked "needs data".
- **Golden students.** Hand-made students with known answers (`golden/`), including Maria, Priya
  and Dana from your doc, are solved against the JSON. With your examples, 15 of 15 come out right.

To make sure the cases have teeth, the tests break your JSON on purpose (four electives becomes three,
the 400+ check is dropped, `choose 1` track becomes `choose 2`, Religion's root checks are dropped),
and each break must flip at least one verdict. Two findings from doing this:

1. Under slot assignment, `eq` and `min` give the same verdict, because the solver can always leave an
   extra course unused (your free-elective point). The `eq` rule still matters for any checker that
   counts every eligible course, so `check_taxonomy.py` keeps enforcing it.
2. The Health track's 8-unit elective threshold is implied by the 28-unit track check (20 units of
   required courses + 8), so no student can tell them apart. That's redundant, not wrong.

```bash
python check_bip.py                        # your examples
python check_bip.py --program-dir out_v2   # the model's output after T15, same students
```

Cases exist for Economics, Public Policy and Religion so far. Anthropology and Behavioral Economics
are next.

## Rewrite map: every current example, and what it becomes

| Current section and example | New encoding | Task |
|---|---|---|
| **Header**: "five families", filter / measure / bound, `scope` | Tree intro + vocabulary glossary. `scope` is removed (nesting or `of_which` replaces it) | T7, T12 |
| **Normalizing** paragraph | "Choose N" and bare numbers mean `min`; `eq` only for "exactly" | T5 |
| **When two families both fit** | Decision guide: picks courses → `count`; condition on courses already picked → `of_which`; explicit exception to the one-slot rule → `course_reuse`; timing → `sequencing`; no checkable rule → `unresolved` | T12 |
| Course Selection: choose 3 of CSCI 201/270/310/350 | `count`, `{"courses": [...]}`, `courses min 3` | T1, T5 |
| Course Selection: all of PHIL 350/351/352 | `all_of` of `specific_course` | T13 |
| Course Selection: BUAD 302 and 304, one of 306/307 | `all_of` with a nested `choose 1` | T13 |
| Course Selection: 12 units of MUSC 300+ | `count`, `prefix` + `level_min`, `units min 12` | T1 |
| Course Selection: history "approved offerings" | `count` with `unresolved` + the three rules | T4 |
| Course Selection: choose a track by name | **Removed.** Replaced by the Public Policy nested-tracks example | T13 |
| Distribution Bounds: Law / Other electives, min 4 / max 8 each | `count` (12 units) with two `of_which` checks | T8, T12 |
| Distribution Bounds: four courses, one from each of three groups | `count` with one check per group | T8 |
| Distribution Bounds: 24 of 32 units upper-division | Root `of_which` (the real Religion sentence) | T8 |
| Distribution Bounds: at most 2 of 9 at the 100/200 level | `of_which` on the group, `level_max 299`, `max 2` | T8 |
| Distribution Bounds: at most 2 courses outside the college | Root `of_which`, `{"not": {"school": "Dornsife"}}` | T1, T8 |
| Distribution Bounds: 104 units in the college's departments | `unclassified`, `university_level` (Q4) | T11 |
| Distribution Bounds: 12 units in any one department | `unclassified`, `out_of_scope` (per-department limits are Phase 2) | T11 |
| Distribution Bounds: three different departments | `of_which`, `count_by: departments`, `min 3` | T8 |
| Distribution Bounds: "half of the elective units" (prose) | **No fit.** The schema has no fractions (Q3) | T3 |
| Course Reuse: `PROHIBITS` | **Removed.** The one-slot rule covers it; it becomes a `note` | T12 |
| Course Reuse: double-count ≤ 3 / 4 courses unique to the minor | `course_reuse` placeholders, `kind` moved up out of `details` | T12 |
| Course Reuse: one of TAC 115 / 116 / CSCI 103L / 113x | Root `of_which`, `courses` list, `max 1` | T12 |
| Sequencing ×3 | `sequencing` placeholders: rename the family, move `kind` up | T12 |
| Manual Review ×9 | `manual_review` placeholders; the two `eq` become `min`; `NO_POOL` may become `unresolved` (Q2) | T5, T12 |
| Out of scope: "emit nothing" table | `unclassified` with a `reason`; adds `university_level` and `advisory` | T11 |
| Out of scope: admission + GPA | GATE placeholder kept; the GPA clause goes to `unclassified`, `out_of_scope` | T11 |
| _(new)_ | Groups and nesting, the one-slot rule, `of_which`, root and anchored nodes, the heading rule, amendments, `source_lines` / `source_quote` | T8, T13 |

Of the 31 examples, 12 are re-encoded into the new core shapes, 2 move to `unclassified`, 1 is
removed, 1 is replaced, and 15 are placeholders that change mechanically (rename the family, move
`kind` up). This is in addition to the five new sections.

## Outline of the new `constraint_taxonomy.md`

This is the order the model will read it in. Each section builds on the one before.

1. **How to read this.** The tree in one paragraph, a glossary table, and the normalizing rules.
2. **Leaves.** `specific_course`; `count` (the `eligible_if` vocabulary, `unresolved`, `thresholds`).
3. **Groups.** `all_of`, `choose`, nesting, the choose-vs-count rule (Q1), the one-slot rule.
4. **`of_which`.** One example each on a leaf, a group and the root, plus the wording convention.
5. **A whole program.** Root, anchored nodes, the heading rule, amendments, citing by line number.
6. **Not encoded.** `unclassified` and its four reasons.
7. **Placeholder families.** `course_reuse`, `sequencing`, `manual_review`, marked "changes in Phase 2".

Examples will be real catalogue sentences, taken from the five `examples/` programs where
possible, and written out in full.

## Next

1. Rewrite `constraint_taxonomy.md` to the outline until `check_taxonomy.py` passes (T1, T4–T8, T11–T13).
2. `prompt_v2.txt` and line numbering in `run_classifier.py` (T9, T10).
3. Extend `check_results.py` with the same checks plus the cross-node ones (T14). It will reuse
   `check_taxonomy.check_object`.
4. Re-run the 15 test files and compare against `examples/` (T15).
