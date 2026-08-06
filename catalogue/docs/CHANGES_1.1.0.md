# Changes in 1.1.0 (2026-07-13) — first live-site validation on macOS

This copy of the scraper lives inside **USC Catalogue Collector.app** and was
validated against the real catalogue.usc.edu for the first time (the 1.0.0
build was developed in a sandbox that could not reach the site). Live findings
and fixes, each locked by the test suite (170 tests passing):

1. **AWS WAF challenge** — `content.php`/`preview_program.php` return an empty
   HTTP 202 (`x-amzn-waf-action: challenge`) to plain clients. No code change
   needed: the browser layer passes the JS challenge (headless works), and the
   persistent profile's token then lets later fetches succeed via
   `direct_html`. Confirmed working.
2. **No section headings on the live Programs page** — the 2026-2027 page has
   only the page-title h1 plus visual `<p><strong>` degree-type labels
   (Bachelor's Degree, Combined Major, Minor, ...). The app launcher therefore
   runs a retry ladder: strict "Undergraduate Programs" → page h1
   ("Programs, Minors and Certificates") with `--no-strict` (whole-list
   discovery, classifier decides every link) → "Bachelor's Degree".
   Live result 2026-2027: 207 included / 886 excluded / 57 manual review.
3. **clean_content crash** (`AttributeError: 'NoneType' object has no
   attribute 'get'`) — decomposing an element orphans descendants still queued
   in the iteration list (bs4 >= 4.13 sets their attrs to None). Guarded with
   `el.decomposed`.
4. **Layout-table flattening** — the live pages nest all content in
   single-column `table_default` scaffolding; the renderer flattened whole
   pages into one table row. Single-column / role=presentation tables now
   unwrap to normal block flow; real multi-column tables keep the TABLE
   rendering (regression test added).
5. **Container scoring** — `body` outscored the precise `td.block_content`
   region on live pages. Acalog-specific selector candidates now get a +50
   precision bonus.
6. **Live chrome stripped** — `.gateway-toolbar`, `.acalog-icon`,
   `.acalog_catalog_name`, `.acalog-breadcrumb` noise selectors; "Close",
   "Help", "Print Degree Planner" interface lines, including the direct-HTML
   variant that joins interface links on one line with "|".
7. **Breadcrumbs** — captured from the page's `.acalog-breadcrumb` element (or
   a short "Return to" anchor) instead of a regex over flowing page text that
   ran on into prose.
8. **School field** — the run-on school guess was removed; live pages have no
   short school element, and an empty field is preferable to a wrong one.

Quality gates re-run after all changes: pytest 170 passed, ruff clean,
ruff format clean, mypy clean. Live verification: 3 programs (2026-2027) and
2 programs (2024-2025, archived year via auto catoid/navoid resolution)
extracted end-to-end; `audit` passed all checks on the live collection.
