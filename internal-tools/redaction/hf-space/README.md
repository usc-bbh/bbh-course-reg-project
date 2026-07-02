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

## Contents

This Space is a deployment bundle. `app.py` + `requirements.txt` + the
`redactors/` package (a copy of the canonical package in
`internal-tools/redaction/redactors/` of the main repo). If the redaction logic
changes there, re-copy `redactors/` here.

Licensed AGPL-3.0 because it uses MuPDF/PyMuPDF.
