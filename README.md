# bbh-course-reg-project

## Repository layout

- `stars-parser/` — the client-side STARS report parser used by the TrojanReg app.

## STARS report redactor — lives in its own repo

The tool that de-identifies real STARS report PDFs (removing student PII and
replacing grades with pass/fail markers) has its own repository and Hugging Face
Space, which auto-deploys the live web app:

**https://huggingface.co/spaces/StrangeIB/STARSRedacter**

That repo is the single home for the redactor — the web app (`app.py`), the
redaction engine (`redactors/`), and the command-line tool (`redact_stars.py`).
Edit redaction code there, not here. (It used to live in `internal-tools/` in
this repo; see git history before this commit.)