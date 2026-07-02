"""Grade redaction pass  (basis + pass/fail only).

Replaces each actual course grade with a token that preserves ONLY the grading
basis and the university-level pass/fail outcome, hiding the precise grade:

    letter A-..D-  (earns undergrad credit)  -> "Lp"   (letter, passed)
    letter F                                 -> "Lf"   (letter, failed)
    P   (Pass, P/NP basis)                   -> "Pp"   (P/NP, passed)
    NP  (No Pass, P/NP basis)                -> "Pn"   (P/NP, not passed)

Deliberately KEPT untouched (status / basis, not a performance value):
    CR NC  (credit / no-credit basis),  IN IX (incomplete / expired),
    MG NS  (missing / not submitted),   RG (in progress), TR (transfer),
    W (withdrawn), and all ">" course flags.

Also neutralizes the printed GPA and POINTS summary figures (the only numbers
in the report written with THREE decimals, e.g. "3.107", "174.000"), so the
grades cannot be reverse-engineered from the summaries.  Unit tallies use two
decimals ("93.00 UNITS") and are left intact — the degree verifier needs them.

Grades are located structurally: in a course row the grade is the word
immediately following the units field (a 1-decimal number like "4.0"), which
cleanly separates it from the suffix letters (L/X/G) that precede the units.
The legend / grade-definition text has no units field, so it is never touched.
"""
import re
from collections import defaultdict

import fitz

UNITS_RE = re.compile(r"^\d+\.\d$")      # course units: one decimal (4.0, 3.3)
DEC3_RE = re.compile(r"^\d+\.\d{3}$")    # GPA / POINTS: three decimals

# grade -> replacement token (only these are replaced)
REPLACE = {g: "Lp" for g in
           ("A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-")}
REPLACE["F"] = "Lf"
REPLACE["P"] = "Pp"
REPLACE["NP"] = "Pn"
RAW_GRADES = set(REPLACE)  # tokens that must NOT survive after a units field


def _lines(page):
    """Group a page's words into (block, line) rows, each sorted left->right."""
    groups = defaultdict(list)
    for w in page.get_text("words"):        # (x0,y0,x1,y1, word, block, line, n)
        groups[(w[5], w[6])].append(w)
    for ws in groups.values():
        ws.sort(key=lambda w: w[0])
    return groups.values()


def build_findings(doc):
    findings = []
    n_grades = n_gpa = n_rows = 0
    for pno, page in enumerate(doc):
        for ws in _lines(page):
            toks = [w[4] for w in ws]
            for i, t in enumerate(toks):
                if UNITS_RE.match(t):
                    n_rows += 1
                    if i + 1 < len(ws) and toks[i + 1] in REPLACE:
                        gw = ws[i + 1]
                        orig = toks[i + 1]
                        repl = REPLACE[orig]
                        rect = fitz.Rect(gw[:4])
                        pitch = rect.width / max(len(orig), 1)
                        box = fitz.Rect(rect.x0, rect.y0,
                                        rect.x0 + pitch * len(repl), rect.y1)
                        findings.append({"page": pno, "rect": rect,
                                         "box": box, "text": repl})
                        n_grades += 1
        # GPA / POINTS summary numbers (three-decimal) -> X.XXX
        for w in page.get_text("words"):
            if DEC3_RE.match(w[4]):
                rect = fitz.Rect(w[:4])
                findings.append({"page": pno, "rect": rect, "box": rect,
                                 "text": re.sub(r"\d", "X", w[4])})
                n_gpa += 1
    meta = {"grades_replaced": n_grades, "gpa_replaced": n_gpa,
            "course_rows": n_rows}
    return findings, meta


def verify(doc, meta):
    """HARD: any raw letter grade / P / NP still sits after a units field, or a
    three-decimal GPA/POINTS number survived.  No soft warnings."""
    hard = []
    for pno, page in enumerate(doc):
        for ws in _lines(page):
            toks = [w[4] for w in ws]
            for i, t in enumerate(toks):
                if UNITS_RE.match(t) and i + 1 < len(toks) and toks[i + 1] in RAW_GRADES:
                    hard.append(f"raw grade {toks[i + 1]!r} survived after units "
                                f"on page {pno + 1}")
        for w in page.get_text("words"):
            if DEC3_RE.match(w[4]):
                hard.append(f"GPA/POINTS value {w[4]!r} survived on page {pno + 1}")
    return hard, []
