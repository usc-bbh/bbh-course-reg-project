# bbh-course-reg-project

## Repository layout

- `stars-parser/` — the client-side STARS report parser used by the TrojanReg app.
- `internal-tools/` — maintainer-only utilities that are **not** shipped with the app.
  - `internal-tools/redaction/` — de-identifies real STARS report PDFs so they
    can be safely committed and used as design inputs / parser fixtures. One tool
    with a `--redact all|pii|grades` flag (default `all`): the PII pass removes
    student name, address, ID, and sport; the grade pass replaces grades with
    basis + pass/fail tokens and neutralizes GPA figures. See its README for
    usage. Run any `DONOTSHARE_*` report through it and commit only the
    `REDACTED_*` output.