# Degree planner — how we decide what to compute

A design decision, written down so the reasoning survives the people who made it. It governs the degree-planning and what-if tool: given a student's report and a multi-semester plan, does the plan finish the degree?

Background for both documents referenced here: [`01-reading-a-stars-report.md`](01-reading-a-stars-report.md) and [`02-usc-degree-requirements.md`](02-usc-degree-requirements.md).

## The question

For any requirement, there are two ways to know whether a student satisfies it.

- **Read STARS' verdict.** The report already says `OK`, `NO`, or `IP` for every requirement block.
- **Compute it ourselves** from the student's coursework, their approved exceptions, and the requirement definitions scraped from the catalogue.

The original decision was to compute everything, always — one engine, one code path — using STARS' own verdict as a correctness oracle. If our computation reproduced STARS exactly for a student's current major, we could trust it for a hypothetical one.

That is elegant and it is too expensive. Recomputing the university tier means encoding general education in full, which means sourcing USC's category-to-course lists for every catalog year before anything works at all.

## The decision

**Split the work by requirement tier.**

| Tier | Approach |
|---|---|
| University-wide | Reuse STARS' evaluation |
| College or school | Reuse STARS' evaluation |
| Major | Compute from catalogue requirements, coursework and exceptions |
| Minor | Compute, same as major |

Three reasons.

**The upper tiers do not vary in scope.** What-if scenarios are restricted to a different major within the same school, so university and college requirements are identical between the current scenario and the hypothetical one. Recomputing an answer that cannot change is pure cost.

**It takes the largest data dependency off the critical path.** General education category lists move from "required before anything works" to "an enhancement that improves one class of check".

**It keeps the guardrail where the risk is.** The reason to compute rather than trust was the fear that *our* model of the requirements is wrong. That risk lives in the major and minor tiers, which vary per program and which we actually model. University and school rules are few, fixed, and already documented with citations.

## Unsatisfied requirements — carry the gap, don't rebuild the rule

Reuse is obviously safe for a requirement already satisfied. The interesting case is an unsatisfied one, since closing it is exactly what a degree plan is for.

We still do not encode the rule. The report states its own shortfall — twelve units needed, or one course from a named category — so we carry that stated gap forward as an outstanding item. Gaps come in two shapes:

- **Quantitative gaps** — units, grade point averages, residence, upper-division counts. Close these arithmetically against the proposed plan. No external data, works today.
- **Category gaps** — "one course from category C" and similar. These cannot be verified automatically without the category-to-course lists. **Degrade gracefully:** show the requirement as outstanding, let the student nominate which planned course they believe satisfies it, and mark the result unverified. Upgrade to automatic checking once the catalogue data exists.

## What must be computed regardless of tier

Reuse tells you the *current* verdict. It says nothing about a limit a *proposed plan* could newly break. These are cheap and need no external data:

- Physical education at most 4 units; individual music instruction at most 16.
- At most 4 pass/no-pass units toward general education; at most 24 per degree.
- At most 40 upper-division units in any one department, for Dornsife students.
- No double counting, where a planned course is claimed against two requirements.

**The rule of thumb: minimum-type requirements are safe to reuse, because adding courses can only help. Maximum-type and no-double-counting requirements are not, because adding courses can break them.**

## What this costs

The zero-gap regression property now applies to the major and minor tiers only, rather than the whole report. That is an accepted trade — model risk concentrates there, and agreement on a student's current major still licenses confidence in a hypothetical one. Every real report remains a regression test for those tiers.

## Conditions that invalidate this

Recheck the decision if any of these change.

- **Scope.** Valid only while what-ifs stay within one school. A cross-school change moves the college tier, which is then no longer invariant. Cross-school changes are currently out of scope and should warn and route the student to an advisor.
- **Snapshot staleness.** Reusing a tier means inheriting the report's prepared date. Carry that date through and surface it rather than presenting an old verdict as current.
- **Catalog year change.** A student changing catalog year changes the upper-tier rules, so the reused verdict would be for the wrong year.
