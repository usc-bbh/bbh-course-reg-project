# VISHAL_REVIEW_ACTIONS.md

## Status of this document: BLOCKED — review document not found

I was instructed to read Vishal's complete code review before doing anything
else and to convert every point into an actionable checklist. **I could not
locate any such review.** Rather than invent its contents, this file records
exactly what was searched, what was found, and what is needed from you.

### Searches performed (2026-07-30)

| Source | Query | Result |
| --- | --- | --- |
| Slack (all public + private channels, DMs, group DMs) | `Vishal code review catalogue` | 10 unrelated results (BODi campaigns, Apple-team bug lists, CRM threads) |
| Slack | `from:Vishal` | **No results** |
| Slack user directory | `Vishal` | **No such user in the beachbody.slack.com workspace** |
| Slack | `STARS redacter` | **No results** |
| Outlook mail | `Vishal review scraper` | No results |
| Outlook mail | sender contains `vishal` | No results |
| Outlook mail | `USC catalogue scraper` | No results |
| Local filesystem | `grep -ril "vishal\|natalie"` across `~/Desktop/DEEP_WORK /BBH/` | No matches |
| Local filesystem | Spotlight `STARS`, `redact`, `*Vishal*` under `~/Desktop` | No project matches (only macOS system files) |

### Related finding: "STARS Redacter"

The brief names a second project, **STARS Redacter**, as in scope. No such
project exists anywhere on this Desktop, in the BBH folders, in Slack, or in
Outlook. No code, config, output, or documentation for it was found. **No work
was performed on STARS Redacter**, and none is claimed.

### Natalie

The brief instructs me to coordinate implementation decisions with Natalie. The
only "Natalie" in the workspace is **Natalie Dauer**
(`nataliedauer@digitalmediamanagement.com`), who has no messages relating to
this project. I have therefore **not contacted anyone** — sending a message on
your behalf needs your explicit approval, and I could not confirm the right
recipient. The decision list below is written so you can forward it as-is.

### What to do

Send me the review (paste the text, drop the file into
`~/Desktop/USC Scraper Incident Fix/`, or point me at the PR/thread) and I will
convert every item into this checklist format and implement it. Everything
below was found by independent investigation, not from the review, so the
review may well contain items not covered here.

---

## Decisions that require Natalie's (or the reviewer's) approval

The investigation is complete and the defect is fixed (see
`ENGINEERING_REPORT.md`). These five judgement calls are documented, defensible
and implemented — but they change behaviour, so they should be confirmed rather
than assumed.

| # | Decision | What I implemented | Why it needs sign-off | Owner |
| --- | --- | --- | --- | --- |
| 1 | **Fail loudly instead of writing a suspect file.** | A program whose extraction fails validation is **not written**; the program stays pending, an error row is recorded, and the run summary reports it. | Changes the delivery contract: a run may now finish with fewer than 470 files and a non-zero failure count, where previously it always reported "470/470 success" (falsely). | Natalie |
| 2 | **Content-region requirement is structural, not scored.** | For program pages only a true catalogue content region may be used; the whole-document fallback is ineligible at any score. | If USC ever ships a program page without acalog content markup, that page will fail rather than silently degrade. I consider that correct, but it is a deliberate availability-for-correctness trade. | Natalie |
| 3 | **Validation thresholds.** | Semantic evidence (own title heading + course/unit content) decides validity; length is only a 200-char backstop (clean-corpus minimum was 971). | Thresholds are derived from the 470-file corpus, not from policy. If some programmes are legitimately prose-only with no course codes, rule 3 would need relaxing. | Natalie |
| 4 | **Existing files are re-validated on resume.** | A file with an intact hash but contaminated content is re-extracted instead of skipped. | Means the first corrected run over an old output folder rewrites ~158 files. Baseline is preserved separately so nothing is lost. | Natalie |
| 5 | **Corrected data lives in a new folder.** | `05_corrected_output/full/…`; the original 470 files are untouched and read-preserved in `01_baseline/`. | Someone must decide when the corrected set replaces the delivered set, and whether downstream consumers need re-pointing. | Francis + Natalie |

## Deadline

Wednesday morning is treated as fixed. The fix, the full corrected re-scrape,
the audit and the tests are complete as of this session, which leaves the
remaining time for review rather than engineering.
