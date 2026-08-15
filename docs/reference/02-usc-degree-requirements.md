# USC degree requirements

*Vishal Gupta, with Claude support.*

What USC actually requires for an undergraduate degree, and how this project models those requirements in code. Companion to [`01-reading-a-stars-report.md`](01-reading-a-stars-report.md), which covers how a STARS report is laid out rather than what it audits against.

Status tags are the same as in the companion document: `[verified]` sourced with a link, `[inferred]` our reading, `[confirm]` needs the registrar.

As with the companion document, **this is not an official USC document.** Ask an advisor about your own degree — see [USC advising and support](https://www.usc.edu/advising-support/).

> **This document has not had a full verification pass.** Every claim tagged `[inferred]` or `[confirm]` is provisional. Section 7 in particular is operating under an explicitly temporary rule — read it before writing any code that depends on grades.

---

## 1. Requirement tiers

Requirements fall into four tiers. The distinction matters because it determines what actually changes when a student asks "what if I switched majors?"

1. **University-wide** `[verified]` — apply to every undergraduate, whatever their program. The 128-unit minimum, the grade point average floors, the residence requirement, general education, the writing requirement.
2. **College or school** `[verified for Dornsife and Marshall]` — apply once the owning school is known. The school appears in the current-post row of the report.
3. **Major** — the part that changes when a student explores a different major.
4. **Minor** — a minor block layers university-wide minor policy on top of program-specific requirements. Majors do not work this way; for a major, the policy-tier rules stand as separate top-level blocks.

**The practical consequence for what-if analysis.** A student considering a different major **within the same school** does not need the university-level requirements re-examined at all. Those requirements are identical under either major, and the report already states whether each one is satisfied. The same holds for the school tier, since the school has not changed. Only the major tier — and any minor — genuinely differs between the two scenarios.

This is why switching majors *within* a school is a tractable question and switching *across* schools is not. A cross-school change moves the college tier too: a student leaving Dornsife stops owing 104 units in Dornsife departments and the foreign-language requirement, and picks up whatever the new school requires instead. At that point the report's existing verdicts no longer describe the hypothetical, and the honest answer is to send the student to an advisor.

The design consequences of all this are in [`03-degree-planner-architecture.md`](03-degree-planner-architecture.md).

## 2. University-wide requirements `[verified]`

Source: [Requirements for Graduation](https://catalogue.usc.edu/content.php?catoid=16&navoid=6079).

- **Units** — a minimum of 128 baccalaureate units, of which no more than 4 may be physical education and no more than 16 individual music instruction. At least 32 must be upper-division. All upper-division coursework in the major must be completed at USC.
- **Grade point average** — 2.0 across all USC baccalaureate units, 2.0 on combined USC and transfer work, and 2.0 across all upper-division courses applied to the major.
- **Residence** — "A minimum of 64 units toward the bachelor's degree must be earned in residence at USC." Source: [Course Work Taken Elsewhere](https://catalogue.usc.edu/content.php?catoid=22&navoid=9114), under *Undergraduate transfer unit limitations*. Worth knowing this lives on the transfer-limitations page rather than the graduation-requirements page, which only mentions residence in passing.
- **General education, the writing requirement, and a diversity requirement** are listed under degree requirements. The status of the diversity requirement is `[confirm]`.

The physical education and music limits are **caps, not requirements to take those subjects.**

### 2a. Which courses count against the caps `[inferred]`

- **The wording does not match.** The catalogue caps "physical education units"; the report words the same cap as "physical education activity courses". These may not be the same set. `[confirm]`
- **The courses carry the `PHED` prefix**, and the department mixes one-unit activity classes (weight training, yoga, beach volleyball, basketball, varsity athletics) with two- and three-unit academic ones (stress management, coaching, health coaching).
- **Our split between the two is an interpretation, not a designation.** We separated them by description and unit count. No formal per-course "activity" designation appears to exist. The safe interim proxy is to count all `PHED` units.
- **The music cap names specific course numbers, not a level band** `[verified]`. "Individual instruction in music at the 101, 201, 300, 301 and 401 levels" means those applied-lesson course numbers; 300 and 301 are different courses. An unrelated 300-level music course is not covered.
- **For code:** applying these caps to a hypothetical future plan needs per-course type attributes, sourced from the catalogue. It is not needed to reproduce a student's current standing, because the report has already applied them.

## 3. School and college requirements

**Dornsife** `[verified]` — source: [Dornsife policies and requirements](https://dornsife.usc.edu/undergrad-programs/policies/).

- 104 units in Dornsife departments, reduced to 96 with a minor or second bachelor's degree, and 70 for a Dornsife degree administered by a professional school.
- A limit of 40 upper-division units in any one major. This is a Dornsife rule, not a university one.
- Foreign language through the third semester of a language, or placement. Freshmen by their 64th unit, transfers by their 96th.

**Marshall** `[verified, one item to confirm]` — source: the catalogue's business administration program page and Marshall advising. Shared across all business concentrations.

- A business core, surfacing on the report as separate blocks for mathematics, economics, accounting, and required upper-division business courses.
- Twelve units of upper-division business electives, drawn from the Marshall course prefixes. The concentration surfaces as a major-emphasis requirement.
- Sixty units of non-business coursework — Marshall's counterpart to Dornsife's 104. Where this surfaces on the report is `[confirm]`.
- Letter-grade and residence rules on specified courses, and a 2.0 grade point average in upper-division business courses.

**In general** `[inferred]`, each school adds its own tier. We have only confirmed two. Discover the rest as samples arrive.

## 4. Majors, minors, concentrations and tracks

**A minor block carries university minor policy on top of the program's own requirements** `[verified]` — source: Requirements for Graduation, minor programs section. At least 16 units unique to the minor, and a minimum 2.0 grade point average across courses applied to the minor. We confirmed this across three minors from three different schools, which is what makes it university-level rather than school-specific. The grade point average appears in the block header; the unique-units rule appears as a sub-group.

The order of sub-groups within a minor block follows a consistent template `[inferred]` — required courses, then electives, then any caps or options, then the unique-units rule — with absent components skipping their slot.

**Catalog years are keyed differently by credential type.** A minor is a separate credential and carries **its own catalog year**, which can differ from the major's `[verified]`. A concentration, track, or emphasis is part of the major and inherits the major's year `[inferred]`; whether Marshall emphases behave this way is `[confirm]`.

The catalogue uses minor, concentration, track, emphasis and specialization inconsistently. Map them onto one internal model.

## 5. General education

Catalog-year dependent. The current framework is core literacies plus global perspectives.

- **Core literacies** — eight courses spanning six categories: arts, humanistic inquiry, social analysis, life sciences, physical sciences, quantitative reasoning.
- **Global perspectives** — one course from each of two further categories.
- **Entry type forks the requirement.** Students entering as fall freshmen must take a general-education seminar. Transfer and spring-admitted students are exempt from that seminar but must complete at least two core literacy courses at USC.
- **Four validation rules**, taken from the report's own general-education limitations block `[confirm — locate the catalogue source]`: a course counts in only one general-education category; the exception is that a course may satisfy both a core literacy and a global perspective; at most 4 units pass/no-pass may count; only one general-education seminar counts.

**The data dependency worth knowing about:** when a general-education requirement is unmet, the report names a *category*, not a list of courses. Verifying that a proposed course satisfies it requires USC's category-to-course lists per catalog year, from the catalogue rather than the report.

## 6. Representing requirements in code

*Pending.* How degree requirements are classified and represented for the requirements engine is being written up separately, alongside the classification work in [`../../constraint_classifier_prompt.md`](../../constraint_classifier_prompt.md). This section will point there once that is settled.

## 7. Grades, prerequisites, and repeated coursework

> **This section is operating under a temporary rule.** An earlier version conflated two different grade rules. They are separated below, but the resolution is pending confirmation from the registrar. Do not promote anything here to authoritative without that confirmation.

### The stopgap currently in force

Until the question below is settled, the tools operate under a deliberately conservative rule. It is a hedge, not an answer — it warns where we are unsure rather than ruling.

> **Pass rule.** Treat any grade other than `F`, `NP`, `NC`, `IN`, `MG` and `W` as passed. The course counts as taken.
>
> **Caution rule.** Flag any *completed* course graded `C-` or below. These earn units, but may not satisfy prerequisites or major and minor requirements, which frequently require a `C` or better.

### The two rules that must not be conflated

- **Prerequisite satisfaction** governs whether a student may *register* for a course. Prerequisites are stated per-course in the catalogue as a boolean expression of course codes, usually **without any grade attached**. Our reading is that completing the named course at the minimum passing grade satisfies it, unless that course's own prerequisite line says otherwise `[confirm]`.
- **Major and minor application** governs whether a course *counts toward a requirement*. Here the catalogue does impose grade quality — a `C` or higher — and pass/no-pass work generally cannot apply to a major or minor without departmental permission.

Conflating these produces confidently wrong answers in both directions, which is why the stopgap above hedges instead.

### What we believe today

- **The minimum passing grade for undergraduate credit is `D-`** `[verified]`. A `D` earns units, even where it satisfies nothing.
- **Units are earned only with a credit-earning grade** `[verified]`. `F`, `NP` and `NC` earn none. `IN`, `MG` and `NS` earn none until resolved. Credit deleted for repetition, excess, or out-of-sequence enrolment earns none.
- **Grade point average treatment** `[verified]`: an expired incomplete and a unit waiver count as zero points, equivalent to an `F`. Incompletes, missing grades, ungraded credit, pass/no-pass, withdrawals and interim marks do not affect the average.
- **Pass means `C-` or better** `[verified]` — it earns units but no grade points, and pass/no-pass work generally cannot fulfil a major or minor requirement. Caps of 24 units per degree and 4 units toward general education apply.
- **Repeated coursework earns units once** `[verified]`. A course already passed at `B-` or better cannot be repeated for grade-point purposes. First-year forgiveness is limited to the first two semesters, grades of `D+` or below, and at most three courses.
- **Checking prerequisites needs per-course boolean expressions from the catalogue.** The report does not contain them.

## Open questions

These are with the registrar. Anything depending on them is provisional.

- Whether `D-` is sufficient for a prerequisite absent an explicit statement, and whether the `C`-or-higher application rule is university-wide or per program.
- Which `PHED` courses count against the physical education cap.
- Whether the `P` and `W` suffixes map onto global-perspectives categories, and which is which.
- Whether the diversity requirement is still active, and where it is audited.
- Where Marshall's 60-unit non-business requirement surfaces on a report.
- Whether business emphases are separate programs for catalog-year purposes.
