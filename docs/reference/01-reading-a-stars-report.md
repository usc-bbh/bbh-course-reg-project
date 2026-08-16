# Reading a STARS report

*Vishal Gupta, with Claude support.*

A STARS report is USC's degree-progress audit for one student in one program. It is dense, heavily abbreviated, and easy to misread. This document explains how to read one.

## About this document

**This is not an official USC document, and it is not authoritative.** It was assembled by reading real STARS reports alongside the USC Catalogue and inferring how the two fit together. Some of what follows is confirmed against published USC policy; some is our best reading of the evidence. Every claim is tagged so you can tell which is which.

**If you have a question about your own STARS report, ask an advisor** — see [USC advising and support](https://www.usc.edu/advising-support/). Advising is organised by school, so your own school's advising office is the right place to start. Your advisor and the Catalogue are authoritative; this document is not, and nothing here should be relied on for a decision about your degree.

Thanks are due to USC Advising for clarifying several questions along the way. Any errors that remain are mine.

## Who this is for

Two different readers, with different needs:

- **Students** trying to understand what their own report is telling them. Most of this document is for you. You can skip anything marked as being for the code.
- **Developers** writing code in this repository that consumes STARS reports. Passages addressed specifically to you are called out as such.

## Status tags

| Tag | Meaning |
|---|---|
| `[verified]` | Sourced from USC documentation; link inline |
| `[inferred]` | Our reading of the evidence, not yet confirmed |
| `[confirm]` | Needs confirmation from the registrar or advising |

Take `[inferred]` and `[confirm]` seriously — several are load-bearing.

---

## Core conventions

**Term codes are `YYYY` plus a term digit**, where 1 is spring, 2 is summer, 3 is fall. So `20243` is fall 2024 and `20251` is spring 2025.

**Class level comes from units earned, not time enrolled** `[verified]`. Freshman is under 32 units, sophomore 32 to 63.9, junior 64 to 95.9, senior 96 and above. This diverges from how long you have been at USC whenever transfer credit is involved — a student who entered last fall can already be a senior.

**A report is a point-in-time snapshot.** The `PREPARED` date at the top is the moment it describes. Two reports for the same student on different dates can legitimately disagree, and an older report can show a requirement as unmet that has since been satisfied. Check the date before trusting anything on the page.

**A double major produces one report per major.** There is no consolidated report — a student with two majors gets two separate documents, each repeating the university and school requirements and carrying its own major section.

**Section dividers segment the document.** Rows of underscores separate most blocks, rows of equals signs bracket the administrative blocks near the top, and rows of asterisks frame banners such as the legend and the closing disclaimer.

## Which STARS report you are looking at

Several systems around USC display STARS data, and they format it slightly differently — different column layouts, different amounts of surrounding page furniture. This is annoying, and it means a description of one layout does not automatically describe another.

**This document describes one specific artefact: the single-column report produced by a print-to-PDF from `experience.usc.edu`.** That is the version students can most easily generate themselves, and the version this project is built around. Its body matches the older single-column report layout, so the interpretation below carries over.

That export is text-layered rather than scanned, so the text can be selected and copied. On screen it is colour-coded, blue for satisfied and red for unsatisfied. Copying the text loses the colour, but the `OK` and `No` codes survive, so no meaning is lost.

## Where the personal information sits

A real STARS report identifies the student. The name and ID appear in the print preamble at the top of the export, the name and mailing address appear in the diploma information block, and a per-page header carries a timestamp alongside the source URL.

**For those of you coding against STARS reports in this repository:** you will usually be working with *redacted* sample reports, which have had this material stripped or replaced. That has two consequences worth internalising.

- **Never anchor on line numbers or byte offsets.** Redaction changes the length of the preamble and the diploma block, so any offset measured on one report will be wrong on another. Anchor on content instead — the first `PREPARED:` or `PROGRAM:` line, the divider rows, the requirement status codes.
- **Expect the page headers and footers to interleave with real content.** They repeat at every page break and can land in the middle of a requirement block, splitting it across the boundary. Filter them out before parsing anything else.

Neither the preamble nor the diploma block contains anything a tool needs. Everything downstream depends on the report body.

## What is in a report, in order

1. **Header** — prepared date, student ID, name, program code, catalog year, degree, major.
2. **Pertinent data** — term of USC entrance, class level, expected graduation.
3. **Diploma information** — printed name and mailing address. Administrative only.
4. **Current post** — the degree, major, unit and effective-term row. Your **owning school** appears here for the first time. Followed by the minor line, the advisor line, and, for athletes only, a student-athlete line.
5. **Status banner and time to degree** — whether all requirements are satisfied, and an estimate of semesters remaining.
6. **The unit requirement and master course list** — the authoritative list of completed, degree-applicable coursework.
7. **University requirement blocks** — grade point average, residence, upper-division units.
8. **Writing and foreign language.**
9. **General education** — core literacies and global perspectives.
10. **Major requirements**, including any concentration or track.
11. **Minor requirements** — one block per declared minor.
12. **Unit caps, current registration, and "other courses in your academic account".**
13. **NCAA supplemental section** — athletes only. This is an athletic-eligibility audit, not a degree audit, and it re-lists coursework that already appears elsewhere. It is not a second set of degree requirements.
14. **Legend.**
15. **Disclaimer** — boilerplate, but note it states that any approved exceptions should appear on the report.

Sections appear and disappear depending on the student: an athlete has section 13, a student with no minor has no section 11. Completion status also changes how much is printed — a satisfied requirement collapses to a line, while an unsatisfied one expands to show what is missing.

**For the code:** parse by anchors, never by position. Detect the boundaries of the NCAA section and skip it entirely — parsing it double-counts coursework and inflates any ledger.

## The legend

Every report ends with a legend. It is authoritative and worth learning.

**Requirement status codes.** `OK` requirement complete, `NO` requirement incomplete, `+` sub-requirement met, `-` sub-requirement not met.

Block-level `IP` also appears on reports but is **not defined in the legend**. It appears to mean "satisfied only if in-progress courses are counted" `[inferred]` `[confirm]`.

**Course suffixes.** `G` general education, `L` has a lab, `X` credit restriction, `M` meets diversity, `P` meets traditions and historical foundations, `W` meets citizenship in a global era.

**Grade definitions.** `TR` transfer, `RG` current registration, `IN` incomplete, `IX` expired incomplete, `MG` missing grade, `NS` grade not submitted.

**Course flags.** `>D` credit deleted but included in GPA, `>Z` credit deleted and excluded from GPA, `>FF` transfer and freshman forgiveness excluded from GPA, `>R` repeatable, `>IP` in progress, `>EX` excess credit deleted but included in GPA, `R` required sub-requirement, `(R)` required course, `>OS` taken out of sequence with no unit or GPA credit, `>P` taken pass/no-pass.

**Exception codes.** `RE` requirement exchange, `RA` requirement alternative, `CW` course waiver, `UW` unit waiver, `RW` requirement waiver.

## Reading a course row

The grammar is `TERM  COURSE  [suffixes]  UNITS  GRADE  [>flags]  TITLE`.

An in-progress row looks like `20263 ENST450 4.0 RG >IP Sustainability in Practice` — fall 2026, no grade yet. A completed row looks like `20253 ENST360 4.0 A- Public Policy…`, with a real grade and no in-progress flag.

**`RG` and `>IP` describe the same situation from two angles.** `RG` sits in the grade column and means "registered, no grade yet". `>IP` sits in the flags column and means "in progress". They co-occur, and they include registrations for future terms. Either one means the course is underway and its units are not yet earned.

**Titles are truncated to a fixed width.** *For the code:* the course code is the reliable key; the title is not.

## Reading a requirement block

**There are two levels of status.** The block carries `OK`, `NO`, or `IP`. Within a nested block, each numbered sub-requirement carries `+` or `-`.

**Blocks are flat or nested.** A grade point average requirement is flat. A major requirement is usually nested — numbered sub-requirements, each with its own status and course list.

**`R` and `(R)` mark what is mandatory.** `R` marks a required sub-requirement, as opposed to a choose-from group. `(R)` marks a specific required course, as opposed to one option in a list. An unmet `R` is a hard gap; an unmet non-`R` group can usually be satisfied several ways.

**The trailing label on a tally tells you what kind of number it is** — `UNITS` a unit count, `SUB-GROUP(S)` a count of satisfied sub-requirements, `COURSES` a count of courses applied, and `GPA` a grade point average.

**The label for an average is not consistent across report sources** `[verified by inspection]`. The `experience.usc.edu` exports this project targets use `GPA`, as in `EARNED: 3.521 GPA` — confirmed across four separate exports. A legacy single-column variant supplied directly by the registrar uses `AVE` instead, as in `EARNED: 3.166 AVE`. *For the code:* anchor on `GPA`, since that is what the supported export contains. Accepting `AVE` as an alternative costs nothing if you want the safety margin, but do not build out legacy-report support beyond that.

**`NEEDS`, `EARNED`, and `IN-PROCESS`** state what is outstanding versus done. **`SELECT FROM`** lists what would satisfy an unmet item — explicit courses for a major requirement, but for general education only a *category* pointer such as `CATEGORY GE-C`. Turning a category into an actual list of courses needs the Catalogue; the report does not contain it.

**The numbering of sub-groups can jump**, going from `1)` to `3)`. This is a fixed-slot template with unused slots omitted — a block with no elective component simply skips that number. *For the code:* do not map STARS numbering one-to-one onto the Catalogue.

## Transfer credit appears in four places

1. **An aggregate line**, `99993 TRNSFR WORK … TR — Total Transfer Units`. A roll-up total, not a course.
2. **Inside requirement blocks**, where an individual transfer satisfied a named requirement, often via an exchange or alternative exception.
3. **Under "other courses in your academic account"**, for transfers not applied to any named requirement.
4. **In the NCAA section** for athletes, which re-lists some of the above.

**The duplication is partial.** Individual transfers are partitioned between locations 2 and 3 — a course is generally in one or the other, though it can appear in several requirement blocks if it satisfies several requirements. Location 1 is a summary that adds no new courses. Location 4 duplicates.

There is **no consolidated transfer list and no articulation table**. Articulated transfers appear inline under their USC-equivalent course code. Transfers with no USC equivalent appear as generic `TR-` placeholders, and those placeholders **cannot satisfy a specific USC prerequisite** — if you transferred a course that came across as a generic placeholder, it counts toward your unit total but will not clear a prerequisite for a specific USC course.

## "Other courses in your academic account"

These are courses on your record that were not applied to any named requirement — unused transfer credit, physical education, in-progress work.

**They still count toward your total unit requirement as free electives.** On one sample report the unit block showed 97 units earned, which reconciles exactly as 69 units of USC-resident coursework plus 28 units of transfer credit, and that transfer total includes the unapplied transfers listed in this section. So a course appearing here is not wasted; it just is not filling a named requirement.

A petition can move a course out of this section into a named requirement block. That does not change the fact that it was already contributing units.

## Unit caps

**Physical education is capped at 4 units.** Courses carry the `PHED` prefix. Exactly which `PHED` courses count is `[confirm]` — the Catalogue says "physical education units" while the report says "activity courses", and the department offers both one-unit activity classes and two- and three-unit academic ones.

**Individual music instruction is capped at 16 units.** The cap names specific course numbers — 101, 201, 300, 301, 401 — rather than a level band. 300 and 301 are different courses, and an unrelated 300-level music course is not covered.

Both are caps, not requirements to take those subjects.

## What is still unconfirmed

- Whether block-level `IP` means exactly "satisfied when in-progress courses are counted".
- Which `PHED` courses count against the 4-unit cap.
- Whether the `P` and `W` course suffixes map onto general-education global-perspectives categories `G` and `H`, and which is which.
- Whether the `M` suffix reflects a diversity requirement that is still active, and where it is audited.

These are open questions with USC. If one of them matters to your situation, ask your advisor rather than relying on this page.
