# Contributing

Short version: work on a branch, open a PR, don't commit real student data.

## Before you start

- Accept your invite to the [`usc-bbh`](https://github.com/usc-bbh) organization. All BBH work
  lives there — not under personal accounts.
- Read [`docs/reference/`](docs/reference/) first. It explains USC's degree requirements and how
  to read a STARS report. The code assumes that domain knowledge.
- Tests: see [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md).

```bash
git clone https://github.com/usc-bbh/bbh-course-reg-project.git
cd bbh-course-reg-project
```

If you cloned this before it moved to the org, just repoint your existing copy:

```bash
git remote set-url origin https://github.com/usc-bbh/bbh-course-reg-project.git
git fetch
```

## Never commit

**Real STARS reports, or anything extracted from one.** This is the rule that matters most, and
it is not covered by `.gitignore` — a file committed once stays in git history forever, even if
you delete it in a later commit. Public repo, permanent record.

Use the shared mock fixtures instead:

- `fixtures/stars/` — canonical mock STARS data (parser output *and* validator input)
- `stars-parser/test/fixtures/` — scrubbed parser fixtures

If you need a new fixture, redact it first and have someone else check it before committing. Sport
or team affiliation, class level, and a full grade transcript can identify a student together even
with the name removed.

Also never commit: passwords, API keys, `.env` files, USC VPN credentials, or anything from
`.streamlit/secrets.toml`.

## Workflow

Branch, push, open a PR:

```bash
git checkout -b yourname/what-youre-doing
# ... work ...
git push -u origin yourname/what-youre-doing
```

Then open the PR from the link GitHub prints.

PRs aren't strictly required right now — you *can* push small, safe changes straight to `main`.
But default to a branch for anything that touches shared code, and tag someone for a look. Review
is encouraged, not enforced; that will tighten once modules are closer to final.

Two things are enforced on `main`:

- **No force pushes.** `git push --force` to `main` is rejected.
- **No deleting the branch.**

Both exist because they're the mistakes that can't be undone. A bad commit on `main` is one
`git revert` away and nobody will be upset about it.

## Module notes

The repo is a monorepo of loosely coupled modules — see the layout table in
[`README.md`](README.md). Each has its own README with a schema contract; read it before changing
that module's inputs or outputs.

- `stars-parser/` — JavaScript, runs client-side (PDF.js, Tesseract.js)
- `validator/` — Python, plus a React GUI that runs it via Pyodide (`validator/requirements-dev.txt`)
- `catalogue_scraper/` — Python, scrapes degree *requirements*
- `catalog/` — Python, scrapes the Schedule of Classes; **requires USC VPN**

Changing a schema that another module consumes? Say so in the PR description and flag whoever
owns the downstream module.

## Questions

Ask in Slack before you're stuck for more than an hour. If you're unsure whether something counts
as sensitive data, it does — ask first.
