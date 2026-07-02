# bbh-course-reg-project

## Repository layout

- `stars-parser/` — the client-side STARS report parser used by the TrojanReg app.

## ⚠️ Note: the STARS redactor is a separate internal tool — NOT in this repo

The tool that de-identifies real STARS report PDFs (removes student PII and
replaces grades with pass/fail markers) is an **internal maintainer tool** and
is deliberately **not** part of this repository. **Do not add redaction code
here.** It lives in its own repo / Hugging Face Space, which auto-deploys the
live web app:

> **https://huggingface.co/spaces/StrangeIB/buai-builder-hub**

That repo is the single home for the redactor — `app.py` (web UI), `redactors/`
(engine), and `redact_stars.py` (CLI). Edit redaction code there, not here.
(It previously lived under `internal-tools/` in this repo; see git history
before this commit.)