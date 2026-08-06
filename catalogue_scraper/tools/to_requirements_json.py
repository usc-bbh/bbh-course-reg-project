#!/usr/bin/env python3
"""Convert scraped programme .txt files into structured requirements JSON.

Consumer: the degree-audit engine (Natalie). The .txt files are the faithful
source of record; this produces the machine-readable shape an audit engine can
categorise against.

`_schema_version: 1.0` — PROPOSED. See docs/REQUIREMENTS_JSON_SCHEMA.md. The
field names are a starting point, not a settled contract; the audit engine owner
should confirm or amend them, and this script + that doc change together.

Design rules
------------
* Never invent. Every course entry carries the exact source line it came from,
  so any parse can be traced back and disputed.
* Never silently drop. Prose that is not a course line is preserved in the
  owning section's `notes`, so nothing in the catalogue text is lost.
* Requirement *relationships* USC states in prose ("choose one", "or") are
  captured as `choice_group` / `alternatives` where they are unambiguous, and
  left as `notes` where they are not. Ambiguity is reported, not guessed.

Usage:
    python3 tools/to_requirements_json.py CORPUS_DIR OUT_DIR
      CORPUS_DIR  a collection folder containing programs/*.txt
      OUT_DIR     receives one .json per programme + programmes_index.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = "1.0"
MARKER = "OFFICIAL CATALOGUE CONTENT"

# "CSCI 104", "BISC 120Lg", "MATH 118gx", "ENST 320a"
COURSE_RE = re.compile(r"^(?P<code>[A-Z]{2,5}\s\d{3}[A-Za-z]{0,3})\b(?P<rest>.*)$")
UNITS_RE = re.compile(r"\bUnits?:\s*(\d+(?:\.\d+)?)", re.I)
# A programme TOTAL must come from phrasing that unambiguously describes the
# programme. A bare "\d+ units" must never be treated as the total: e.g.
# Accounting (BS) contains "may complete a maximum of 12 units from the Marshall
# School", which is a restriction, not the degree total. Guessing there would
# produce confidently wrong audit data.
TOTAL_UNITS_RE = re.compile(r"Total units:\s*(\d+(?:\.\d+)?)", re.I)
PROGRAMME_TOTAL_PATTERNS = (
    re.compile(r"\bTotal units:\s*(\d+(?:\.\d+)?)", re.I),
    re.compile(
        r"\b(?:program|programme|major|minor|degree)\s+requires\s+(?:a\s+)?"
        r"(?:minimum\s+of\s+)?(\d+(?:\.\d+)?)\s+units\b",
        re.I,
    ),
    re.compile(r"\brequires\s+a\s+minimum\s+of\s+(\d+(?:\.\d+)?)\s+units\b", re.I),
    re.compile(
        r"\bis\s+a\s+(\d+(?:\.\d+)?)[-\s]unit\s+(?:program|programme|degree|major|minor)\b", re.I
    ),
    re.compile(r"\bThe\s+minor\s+requires\s+(\d+(?:\.\d+)?)\s+units\b", re.I),
)
# every units mention, kept verbatim so a human can adjudicate what the total is
ANY_UNITS_RE = re.compile(r"[^.]*?\b\d+(?:\.\d+)?\s+units\b[^.]*\.", re.I)


def programme_total_units(body: str) -> tuple[float | None, str | None]:
    """Return (total, the exact phrase it came from) or (None, None)."""
    for pat in PROGRAMME_TOTAL_PATTERNS:
        m = pat.search(body)
        if m:
            return float(m.group(1)), m.group(0).strip()
    return None, None


HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<text>.+?)\s*$")
CHOICE_RE = re.compile(
    r"\b(choose|select|complete)\b[^.]{0,60}?\b(one|two|three|four|1|2|3|4|at least)\b", re.I
)


def parse_header(head: str) -> dict:
    meta: dict[str, str] = {}
    for line in head.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def parse_programme(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if MARKER not in text:
        raise ValueError(f"{path.name}: missing '{MARKER}' marker")
    head, body = text.split(MARKER, 1)
    meta = parse_header(head)
    lines = body.splitlines()

    sections: list[dict] = []
    current: dict | None = None
    unparsed = 0

    def new_section(title: str, level: int) -> dict:
        return {
            "title": title,
            "level": level,
            "courses": [],
            "notes": [],
            "choice": None,
            "total_units": None,
        }

    for raw in lines:
        line = raw.strip()
        if not line or line == "---":
            continue

        h = HEADING_RE.match(line)
        if h:
            title = h.group("text").strip()
            level = len(h.group("level"))
            # the programme's own title heading is not a requirement section
            if not sections and level == 1:
                continue
            current = new_section(title, level)
            sections.append(current)
            tu = TOTAL_UNITS_RE.search(title)
            if tu:
                current["total_units"] = float(tu.group(1))
            continue

        if current is None:
            current = new_section("(preamble)", 0)
            sections.append(current)

        # list item?
        item = line[1:].strip() if line.startswith(("-", "•", "*")) else line
        if not item:
            continue

        # a bare "or" between two list items marks the previous entries as alternatives
        if item.lower() in ("or", "and"):
            current["notes"].append({"text": item, "source_line": raw})
            if item.lower() == "or" and current["courses"]:
                current["courses"][-1]["alternative_follows"] = True
            continue

        m = COURSE_RE.match(item)
        if m:
            rest = m.group("rest").strip()
            u = UNITS_RE.search(rest)
            title_text = UNITS_RE.sub("", rest).strip(" .,")
            current["courses"].append(
                {
                    "code": re.sub(r"\s+", " ", m.group("code")),
                    "title": title_text or None,
                    "units": float(u.group(1)) if u else None,
                    "source_line": raw,
                }
            )
            continue

        # prose: keep it, and flag stated choice rules
        note = {"text": item, "source_line": raw}
        if CHOICE_RE.search(item):
            note["states_choice_rule"] = True
            if current["choice"] is None:
                current["choice"] = item
        current["notes"].append(note)
        tu = TOTAL_UNITS_RE.search(item)
        if tu and current["total_units"] is None:
            current["total_units"] = float(tu.group(1))
        if not item[0].isupper() and len(item) < 4:
            unparsed += 1

    all_courses = [c for s in sections for c in s["courses"]]
    programme_total = next(
        (s["total_units"] for s in reversed(sections) if s["total_units"] is not None), None
    )
    total_source = None
    if programme_total is None:
        programme_total, total_source = programme_total_units(body)
    else:
        total_source = "Total units: heading"
    # Preserve every units sentence verbatim; the audit engine decides which
    # restrictions matter. Nothing here is interpreted as the programme total.
    unit_statements = [m.strip() for m in ANY_UNITS_RE.findall(body)][:25]

    return {
        "_schema_version": SCHEMA_VERSION,
        "programme": {
            "name": meta.get("Program Name", ""),
            "credential": meta.get("Credential") or None,
            "kind": "minor" if "minor" in meta.get("Program Name", "").lower() else "degree",
            "catalogue_year": meta.get("Catalogue Year", ""),
            "catalogue_identifier": meta.get("Catalogue Identifier", ""),
            "program_identifier": meta.get("Program Identifier", ""),
            "source_url": meta.get("Source URL", ""),
            "source_text_file": path.name,
            "source_content_sha256": meta.get("Content SHA-256", ""),
            "retrieved_at": meta.get("Retrieved At", ""),
        },
        "totals": {
            "stated_total_units": programme_total,
            "stated_total_units_source": total_source,
            "unit_statements_verbatim": unit_statements,
            "course_entry_count": len(all_courses),
            "distinct_course_codes": len({c["code"] for c in all_courses}),
            "section_count": len(sections),
        },
        "sections": sections,
        "parse_warnings": ([f"{unparsed} short unclassified lines"] if unparsed else []),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    corpus, out = Path(sys.argv[1]), Path(sys.argv[2])
    programs = corpus / "programs"
    if not programs.is_dir():
        print(f"ERROR: {programs} not found", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)

    index, failures = [], []
    for p in sorted(programs.glob("*.txt")):
        try:
            doc = parse_programme(p)
        except Exception as e:
            failures.append({"file": p.name, "error": f"{type(e).__name__}: {e}"})
            continue
        dest = out / (p.stem + ".json")
        dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        index.append(
            {
                "file": dest.name,
                "name": doc["programme"]["name"],
                "credential": doc["programme"]["credential"],
                "kind": doc["programme"]["kind"],
                "stated_total_units": doc["totals"]["stated_total_units"],
                "distinct_course_codes": doc["totals"]["distinct_course_codes"],
                "sections": doc["totals"]["section_count"],
            }
        )

    (out / "programmes_index.json").write_text(
        json.dumps(
            {
                "_schema_version": SCHEMA_VERSION,
                "catalogue_year": index[0]["name"] and "2026-2027",
                "programme_count": len(index),
                "degrees": sum(1 for i in index if i["kind"] == "degree"),
                "minors": sum(1 for i in index if i["kind"] == "minor"),
                "conversion_failures": failures,
                "programmes": index,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    no_courses = [i["file"] for i in index if i["distinct_course_codes"] == 0]
    no_total = [i["file"] for i in index if i["stated_total_units"] is None]
    print(f"converted {len(index)} programmes -> {out}")
    print(
        f"  degrees={sum(1 for i in index if i['kind'] == 'degree')} "
        f"minors={sum(1 for i in index if i['kind'] == 'minor')}"
    )
    print(f"  conversion failures: {len(failures)}")
    print(f"  programmes with 0 course codes (prose-only/stub): {len(no_courses)}")
    print(f"  programmes with no stated total units: {len(no_total)}")
    for f in failures[:5]:
        print("   FAIL", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
