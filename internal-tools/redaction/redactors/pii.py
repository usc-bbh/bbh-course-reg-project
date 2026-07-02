"""PII redaction pass.

Detects the student-identifying fields by their template anchors (constant
labels / formats), never by hard-coded student data:

  - Student ID            (10-digit number in the page header)
  - Roster name           ("Last, First, Middle" line under the ID header)
  - Diploma name          (line after "Name as it will appear on your USC Diploma:")
  - Mailing street        (after "Diploma will be mailed to:")
  - Mailing city/state/zip (the line following the street)
  - Sport / team          (between "Student Athlete:" and "Clock Date:")
"""
import re

import fitz

CITY_RE = re.compile(r"^[A-Za-z .'\-]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?\b")
ID_RE = re.compile(r"\b\d{9,10}\b")
ROSTER_RE = re.compile(r"^[A-Z][A-Za-z.'\-]+(?:,\s+[A-Za-z.'\-]+){1,3}$")

TAG_MAP = {
    "Student ID": "ID", "Roster name": "NAME", "Diploma name": "NAME",
    "Mailing street": "ADDRESS", "Mailing city/state/zip": "ADDRESS",
    "Sport/team": "SPORT",
}


def _first_chunk(s):
    """Text up to the first run of 2+ spaces or a column separator '|'."""
    s = s.split("|", 1)[0]
    return re.split(r"\s{2,}", s.strip(), 1)[0].strip()


def _layout_lines(doc):
    lines = []
    for page in doc:
        txt = page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        lines.extend(txt.splitlines())
    return lines


def detect(doc):
    """Return {label: value} of detected identifiers. Missing fields omitted."""
    lines = _layout_lines(doc)
    found = {}

    id_line_idx = None
    for i, ln in enumerate(lines[:8]):
        m = ID_RE.search(ln)
        if m:
            found["Student ID"] = m.group(0)
            id_line_idx = i
            break

    if id_line_idx is not None:
        for ln in lines[id_line_idx + 1: id_line_idx + 4]:
            cand = _first_chunk(ln)
            if cand and ROSTER_RE.match(cand):
                found["Roster name"] = cand
                break

    for i, ln in enumerate(lines):
        low = ln.lower()
        if "name as it will appear on your usc diploma" in low and "Diploma name" not in found:
            for nxt in lines[i + 1: i + 5]:
                cand = _first_chunk(nxt)
                if cand:
                    found["Diploma name"] = cand
                    break
        if "diploma will be mailed to:" in low and "Mailing street" not in found:
            after = ln.split(":", 1)[1] if ":" in ln else ""
            street = _first_chunk(after)
            if street:
                found["Mailing street"] = street
            for nxt in lines[i + 1: i + 4]:
                cand = _first_chunk(nxt)
                if cand and CITY_RE.match(cand):
                    found["Mailing city/state/zip"] = cand
                    break
        if "student athlete:" in low and "Sport/team" not in found:
            m = re.search(r"student athlete:\s*(.*?)\s*(?:clock date:|$)", ln,
                          re.IGNORECASE)
            if m and m.group(1).strip():
                found["Sport/team"] = m.group(1).strip()
    return found


def _filler(value, tag_label=None):
    if tag_label:
        return f"[REDACTED-{tag_label}]"
    return "X" * len(value)


def build_findings(doc, tag=False):
    """Locate every occurrence of every detected value. Returns
    (findings, meta) where meta = {"values": {...}, "missing": [...]}."""
    values = detect(doc)
    findings, missing = [], []
    for label, value in values.items():
        hits = 0
        for pno, page in enumerate(doc):
            for r in page.search_for(value, quads=False):
                findings.append({"page": pno, "rect": fitz.Rect(r),
                                 "box": fitz.Rect(r),
                                 "text": _filler(value, TAG_MAP[label] if tag else None)})
                hits += 1
        if hits == 0:
            missing.append((label, value))
    return findings, {"values": values, "missing": missing}


def verify(doc, meta):
    """Return (hard_failures, soft_warnings) checked on the redacted doc.

    HARD: a full identifier survived (text or metadata), or a detected value
    could not be located.  SOFT: a bare name fragment appears elsewhere (may be
    a coincidental course word) -> flagged for human review, not auto-removed.
    """
    values, missing = meta["values"], meta["missing"]
    per_page = [p.get_text("text") for p in doc]
    corpus = "\n".join(per_page).lower()

    hard = []
    for k, v in values.items():
        if v.lower() in corpus:
            hard.append(f"PII {k} {v!r} survived in text")
    md = doc.metadata
    if any(isinstance(val, str) and val
           and any(v.lower() in val.lower() for v in values.values())
           for val in md.values()):
        hard.append("PII survived in document metadata")
    for label, value in missing:
        hard.append(f"{label} {value!r} could not be located on any page")

    soft = []
    tokens = set()
    for label in ("Roster name", "Diploma name"):
        if label in values:
            for tok in re.split(r"[,\s]+", values[label]):
                if len(tok) >= 4 and tok.isalpha():
                    tokens.add(tok.lower())
    for tok in sorted(tokens):
        pages = [i + 1 for i, t in enumerate(per_page) if tok in t.lower()]
        if pages:
            soft.append((tok, pages))
    return hard, soft
