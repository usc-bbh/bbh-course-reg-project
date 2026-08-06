"""Tests for tools/to_requirements_json.py (the audit-engine converter).

The critical behaviour under test is that the converter NEVER invents a total
unit count. Accounting (BS) contains "may complete a maximum of 12 units from
the Marshall School" — a restriction, not the degree total. An earlier draft
grabbed the first `\\d+ units` it saw and would have reported 12 units for a
128-unit degree.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "to_requirements_json.py"
_spec = importlib.util.spec_from_file_location("to_requirements_json", _TOOL)
assert _spec and _spec.loader
conv = importlib.util.module_from_spec(_spec)
sys.modules["to_requirements_json"] = conv
_spec.loader.exec_module(conv)


def _write(tmp_path: Path, name: str, body: str, program: str = "Physics (BS)") -> Path:
    p = tmp_path / name
    p.write_text(
        f"Program Name: {program}\nCredential: BS\nCatalogue Year: 2026-2027\n"
        f"Program Identifier: poid=99999\nContent SHA-256: abc123\n"
        f"Extraction Status: complete\n\nOFFICIAL CATALOGUE CONTENT\n\n{body}",
        encoding="utf-8",
    )
    return p


def test_total_units_from_heading(tmp_path):
    p = _write(
        tmp_path,
        "a.txt",
        "# Physics (BS)\n\n## Required Courses\n\n"
        "- PHYS 151Lg Mechanics Units: 4\n\n## Total units: 128\n",
    )
    doc = conv.parse_programme(p)
    assert doc["totals"]["stated_total_units"] == 128.0
    assert "Total units" in doc["totals"]["stated_total_units_source"]


def test_total_units_from_prose_phrasing(tmp_path):
    p = _write(
        tmp_path,
        "b.txt",
        "# Physics (BS)\n\nThe BS, Physics degree is a 128-unit "
        "program.\n\n## Required Courses\n\n- PHYS 151 M Units: 4\n",
    )
    doc = conv.parse_programme(p)
    assert doc["totals"]["stated_total_units"] == 128.0


def test_restriction_units_are_never_mistaken_for_the_total(tmp_path):
    """The regression that matters: a restriction must not become the total."""
    p = _write(
        tmp_path,
        "c.txt",
        "# Accounting (BS)\n\nStudents may complete a maximum of "
        "12 units from the Marshall School before admission.\n\n"
        "## Required Courses\n\n- ACCT 370 Reporting Units: 4\n",
        program="Accounting (BS)",
    )
    doc = conv.parse_programme(p)
    assert doc["totals"]["stated_total_units"] is None, "must not guess 12"
    # but the sentence is preserved so a human can adjudicate
    assert any("12 units" in s for s in doc["totals"]["unit_statements_verbatim"])


def test_course_entries_carry_their_source_line(tmp_path):
    p = _write(
        tmp_path,
        "d.txt",
        "# Physics (BS)\n\n## Required Courses\n\n- BISC 120Lg General Biology Units: 4\n",
    )
    doc = conv.parse_programme(p)
    c = doc["sections"][0]["courses"][0]
    assert c["code"] == "BISC 120Lg"  # suffix preserved
    assert c["units"] == 4.0
    assert c["source_line"].strip().startswith("- BISC 120Lg")


def test_or_marks_the_previous_entry_as_having_an_alternative(tmp_path):
    p = _write(
        tmp_path,
        "e.txt",
        "# Physics (BS)\n\n## Math\n\n"
        "- MATH 126g Calculus II Units: 4\n- or\n"
        "- MATH 129 Calculus II Engineers Units: 4\n",
    )
    doc = conv.parse_programme(p)
    courses = doc["sections"][0]["courses"]
    assert courses[0].get("alternative_follows") is True
    assert courses[1].get("alternative_follows") is None


def test_choice_rules_are_flagged_not_interpreted(tmp_path):
    p = _write(
        tmp_path,
        "f.txt",
        "# Physics (BS)\n\n## Electives\n\n"
        "Choose one design course (4 units) from the following list:\n"
        "- CE 450 Coastal Units: 4\n",
    )
    doc = conv.parse_programme(p)
    sec = doc["sections"][0]
    assert sec["choice"] and "Choose one" in sec["choice"]
    assert any(n.get("states_choice_rule") for n in sec["notes"])


def test_prose_is_never_dropped(tmp_path):
    prose = "Academic advisement is provided through the department office."
    p = _write(tmp_path, "g.txt", f"# Physics (BS)\n\n## Advisement\n\n{prose}\n")
    doc = conv.parse_programme(p)
    assert any(prose in n["text"] for n in doc["sections"][0]["notes"])


def test_prose_only_programme_yields_zero_courses_without_failing(tmp_path):
    p = _write(
        tmp_path,
        "h.txt",
        "# Interdisciplinary Studies (BA)\n\n## Admission\n\n"
        "Admission is by application to a special committee.\n",
        program="Interdisciplinary Studies (BA)",
    )
    doc = conv.parse_programme(p)
    assert doc["totals"]["distinct_course_codes"] == 0
    assert doc["sections"], "sections must still be recorded"


def test_minor_is_classified_as_minor(tmp_path):
    p = _write(
        tmp_path,
        "i.txt",
        "# Spanish Minor\n\n## Required\n\n- SPAN 300 Units: 4\n",
        program="Spanish Minor",
    )
    assert conv.parse_programme(p)["programme"]["kind"] == "minor"


def test_missing_content_marker_raises_rather_than_producing_junk(tmp_path):
    p = tmp_path / "j.txt"
    p.write_text("Program Name: Physics (BS)\n\n# Physics (BS)\n- PHYS 151 Units: 4\n")
    with pytest.raises(ValueError, match="marker"):
        conv.parse_programme(p)


def test_schema_version_is_stamped_on_every_document(tmp_path):
    p = _write(tmp_path, "k.txt", "# Physics (BS)\n\n## R\n\n- PHYS 151 M Units: 4\n")
    assert conv.parse_programme(p)["_schema_version"] == conv.SCHEMA_VERSION
