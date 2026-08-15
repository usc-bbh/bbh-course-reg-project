# Reference documentation

Background on USC degree requirements and the STARS degree-progress report, written for anyone joining this project. These describe **USC**, not our code — they should stay useful even as the modules around them change.

| | |
|---|---|
| [`01-reading-a-stars-report.md`](01-reading-a-stars-report.md) | How a STARS report is structured: conventions, section order, the legend, course rows, requirement blocks, transfer credit, unit caps. Start here if you are writing anything that reads a report. |
| [`02-usc-degree-requirements.md`](02-usc-degree-requirements.md) | What USC requires for an undergraduate degree — university, school, major and minor tiers, general education, grades and prerequisites — plus the six-family model we use to represent requirements in code. |
| [`03-degree-planner-architecture.md`](03-degree-planner-architecture.md) | A design decision: which requirements the degree planner recomputes and which it reuses from the report, and why. |

## How to read the status tags

Claims carry a provenance tag, because a fair amount of this was reconstructed from real reports rather than read off a policy page.

- `[verified]` — sourced from USC documentation, with the link inline.
- `[inferred]` — our reading of the evidence. Plausible, not confirmed.
- `[confirm]` — needs an answer from the registrar or advising before anyone relies on it.

**Treat `[inferred]` and `[confirm]` as real warnings.** Each document ends with its open questions; several are load-bearing for correctness, particularly the grade and prerequisite rules in document 02, section 7.

## Contributing

If you confirm something currently tagged `[inferred]` or `[confirm]`, update the tag to `[verified]`, add the source link inline, and remove it from that document's open-questions list. If you find one of these documents contradicting a real report, the report wins — please open an issue with the discrepancy.

Schema contracts for the code modules are **not** here; each module documents its own, and the repository README lists where.
