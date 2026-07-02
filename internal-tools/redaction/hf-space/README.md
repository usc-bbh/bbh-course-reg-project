---
title: STARS Report Redactor
emoji: 🛡️
colorFrom: red
colorTo: gray
sdk: streamlit
app_file: app.py
pinned: false
license: agpl-3.0
---

# STARS Report Redactor

Student-facing web front end for the BUAI Builder Hub (BBH) / BBHCourseReg STARS
redactor. Upload a USC STARS Degree Progress Report PDF; it removes personal
information (name, ID, address, sport) and grades (replaced with pass/fail
markers, GPA blanked) **in memory** and returns a redacted copy. The uploaded
file is never written to disk or stored.

## Configuration

Set a Space **secret** named `APP_PASSPHRASE` to the access phrase. The app
refuses to run without it.

## Contents & the single source of truth

This Space is a deployment bundle: `app.py` + `requirements.txt` + `README.md`,
plus a **copy** of the `redactors/` engine package.

There is exactly one canonical copy of the engine, in
`internal-tools/redaction/redactors/` of the main repo (shared with the CLI).
To avoid a second, drift-prone copy, `redactors/` here is **git-ignored** and
regenerated on demand:

```bash
./build_space.sh        # copies ../redactors -> ./redactors
```

Run that before you upload to / push to the Space. Rule of thumb: **beautify
`app.py` here freely; never hand-edit `redactors/` — change the engine in the
main repo and re-run `build_space.sh`.**

(Longer term, the cleanest de-duplication is to make the engine a
pip-installable package and have this Space install it via `requirements.txt`;
that removes the copy entirely. Not needed to launch.)

Licensed AGPL-3.0 because it uses MuPDF/PyMuPDF.
