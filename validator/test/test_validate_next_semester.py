import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from validate_next_semester import (
    EXPECTED_DEPT_CLEARANCE_SCHEMA_VERSION,
    _check_already_taken,
    _check_d_clearance,
    _check_in_catalog,
    _check_lab_discussion_pairing,
    _check_major_restrictions,
    _check_prereq,
    _check_seat_availability,
    _check_standing,
    _check_time_conflicts,
    _dept_clearance_by_prefix,
    _normalize_code,
    _to_minutes,
    validate_next_semester,
)


# ---- fixtures -------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    import json

    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def stars_summary():
    return load_fixture("mock_stars_report.json")


@pytest.fixture
def planned_courses():
    return load_fixture("mock_planned_courses.json")["planned_courses"]


@pytest.fixture
def course_catalog():
    return load_fixture("mock_course_catalog.json")


@pytest.fixture
def dept_clearance():
    return load_fixture("../../../dept_clearance.json")


# ---- normalize_code ---------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("CSCI 104", "CSCI 104"),
        ("CSCI104", "CSCI 104"),
        ("csci 104", "CSCI 104"),
        ("  CSCI   104  ", "CSCI 104"),
        ("CSCI104A", "CSCI 104A"),
    ],
)
def test_normalize_code(raw, expected):
    assert _normalize_code(raw) == expected


# ---- already taken ---------------------------------------------------------

def test_already_taken_fails_for_completed_course(stars_summary):
    result = _check_already_taken("CSCI 104", stars_summary)
    assert result.status == "fail"


def test_already_taken_warns_for_in_progress_course(stars_summary):
    result = _check_already_taken("CSCI 350", stars_summary)
    assert result.status == "warning"


def test_already_taken_none_for_new_course(stars_summary):
    assert _check_already_taken("CSCI 999", stars_summary) is None


# ---- standing --------------------------------------------------------------

def test_standing_fails_for_freshman_taking_400_level():
    result = _check_standing("CSCI 401", {"classLevel": "Freshman"})
    assert result.status == "fail"


def test_standing_none_for_junior_taking_400_level():
    assert _check_standing("CSCI 401", {"classLevel": "Junior"}) is None


def test_standing_none_for_100_level_regardless_of_class_level():
    assert _check_standing("CSCI 103", {"classLevel": "Freshman"}) is None


def test_standing_none_when_class_level_missing():
    assert _check_standing("CSCI 401", {}) is None


# ---- D-clearance -------------------------------------------------------------

def test_d_clearance_warns_with_department_text(dept_clearance):
    by_prefix = _dept_clearance_by_prefix(dept_clearance)
    entry = {"has_d_clearance": True}
    result = _check_d_clearance("CSCI 426", entry, by_prefix)
    assert result.status == "warning"
    assert any("myviterbi" in r.lower() for r in result.reasons)


def test_d_clearance_none_when_not_required(dept_clearance):
    by_prefix = _dept_clearance_by_prefix(dept_clearance)
    assert _check_d_clearance("CSCI 360", {"has_d_clearance": False}, by_prefix) is None


def test_d_clearance_warns_generically_for_unknown_department(dept_clearance):
    by_prefix = _dept_clearance_by_prefix(dept_clearance)
    result = _check_d_clearance("ZZZZ 100", {"has_d_clearance": True}, by_prefix)
    assert result.status == "warning"
    assert len(result.reasons) == 1  # only the generic reason, no dept-specific text found


def test_d_clearance_schema_version_guard_raises(dept_clearance):
    bad = {**dept_clearance, "_schema_version": "999.0"}
    with pytest.raises(ValueError):
        _dept_clearance_by_prefix(bad)


def test_d_clearance_schema_version_matches_expected(dept_clearance):
    assert dept_clearance["_schema_version"] == EXPECTED_DEPT_CLEARANCE_SCHEMA_VERSION


# ---- prereqs -----------------------------------------------------------------

def test_prereq_fails_when_gpa_below_threshold():
    entry = {"description": "prerequisite: 3.5 gpa"}
    result = _check_prereq("ANTH 491", entry, {"gpa": 3.0, "completedCourses": []})
    assert result.status == "fail"


def test_prereq_passes_when_gpa_meets_threshold():
    entry = {"description": "prerequisite: 3.0 gpa"}
    result = _check_prereq("ANTH 491", entry, {"gpa": 3.4, "completedCourses": []})
    assert result is None


def test_prereq_fails_when_required_course_not_completed():
    entry = {"description": "Prereq: CSCI 104"}
    result = _check_prereq("CSCI 201", entry, {"completedCourses": []})
    assert result.status == "fail"
    assert "CSCI 104" in result.reasons[0]


def test_prereq_passes_when_required_course_completed():
    entry = {"description": "Prereq: CSCI 104"}
    stars = {"completedCourses": [{"code": "CSCI 104"}]}
    assert _check_prereq("CSCI 201", entry, stars) is None


def test_prereq_falls_back_to_warning_when_unparseable():
    entry = {"description": "Prereq: consent of instructor."}
    result = _check_prereq("AHIS 495A", entry, {"completedCourses": []})
    assert result.status == "warning"


def test_prereq_none_when_no_prereq_keyword():
    entry = {"description": "Intro to widgets."}
    assert _check_prereq("CSCI 999", entry, {"completedCourses": []}) is None


# ---- in catalog ----------------------------------------------------------

def test_in_catalog_warns_when_course_missing():
    result = _check_in_catalog("CSCI 999", {})
    assert result.status == "warning"


def test_in_catalog_none_when_present():
    assert _check_in_catalog("CSCI 104", {"CSCI 104": {}}) is None


# ---- seat availability -----------------------------------------------------

def test_seat_availability_fails_when_all_sections_full():
    entry = {"sections": {"lectures": [{"section_id": "1", "is_full": True, "is_cancelled": False}]}}
    result = _check_seat_availability("ACCT 371", entry, None)
    assert result.status == "fail"


def test_seat_availability_none_when_some_sections_open():
    entry = {
        "sections": {
            "lectures": [
                {"section_id": "1", "is_full": True, "is_cancelled": False},
                {"section_id": "2", "is_full": False, "is_cancelled": False},
            ]
        }
    }
    assert _check_seat_availability("CSCI 401", entry, None) is None


def test_seat_availability_fails_for_selected_full_section():
    entry = {
        "sections": {
            "lectures": [
                {"section_id": "1", "is_full": True, "is_cancelled": False},
                {"section_id": "2", "is_full": False, "is_cancelled": False},
            ]
        }
    }
    result = _check_seat_availability("CSCI 401", entry, {"1"})
    assert result.status == "fail"


def test_seat_availability_none_for_selected_open_section():
    entry = {
        "sections": {
            "lectures": [
                {"section_id": "1", "is_full": True, "is_cancelled": False},
                {"section_id": "2", "is_full": False, "is_cancelled": False},
            ]
        }
    }
    assert _check_seat_availability("CSCI 401", entry, {"2"}) is None


# ---- lab/discussion pairing -------------------------------------------------

def test_lab_pairing_warns_when_no_sections_selected():
    entry = {"has_lab": True, "has_discussion": False, "sections": {}}
    result = _check_lab_discussion_pairing("CSCI 104", entry, None)
    assert result.status == "warning"


def test_lab_pairing_none_when_link_codes_match():
    entry = {
        "has_lab": True,
        "has_discussion": False,
        "sections": {
            "lectures": [{"section_id": "L1", "link_code": "A"}],
            "labs": [{"section_id": "B1", "link_code": "A"}],
        },
    }
    assert _check_lab_discussion_pairing("CSCI 104", entry, {"L1", "B1"}) is None


def test_lab_pairing_fails_when_link_codes_mismatch():
    entry = {
        "has_lab": False,
        "has_discussion": True,
        "sections": {
            "lectures": [{"section_id": "L1", "link_code": "A"}],
            "discussions": [{"section_id": "D1", "link_code": "B"}],
        },
    }
    result = _check_lab_discussion_pairing("MATH 407", entry, {"L1", "D1"})
    assert result.status == "fail"


def test_lab_pairing_fails_when_required_section_missing():
    entry = {
        "has_lab": True,
        "has_discussion": False,
        "sections": {"lectures": [{"section_id": "L1", "link_code": "A"}]},
    }
    result = _check_lab_discussion_pairing("CSCI 104", entry, {"L1"})
    assert result.status == "fail"


def test_lab_pairing_none_when_not_required():
    entry = {"has_lab": False, "has_discussion": False, "sections": {}}
    assert _check_lab_discussion_pairing("CSCI 360", entry, None) is None


# ---- major restrictions -----------------------------------------------------

def test_major_restrictions_fails_when_reserved_for_other_major():
    entry = {
        "has_restrictions": True,
        "sections": {
            "lectures": [
                {
                    "section_id": "1",
                    "is_cancelled": False,
                    "notes": "This course is reserved for students in the B.S. GeoDesign program.",
                }
            ]
        },
    }
    result = _check_major_restrictions("ARCH 203", entry, {"major": "Computer Science", "classLevel": "Junior"})
    assert result.status == "fail"


def test_major_restrictions_none_when_reserved_for_students_major():
    entry = {
        "has_restrictions": True,
        "sections": {
            "lectures": [
                {
                    "section_id": "1",
                    "is_cancelled": False,
                    "notes": "This course is reserved for students in the Computer Science program.",
                }
            ]
        },
    }
    result = _check_major_restrictions("CSCI 490", entry, {"major": "Computer Science", "classLevel": "Junior"})
    assert result is None


def test_major_restrictions_fails_when_undergrad_only_but_student_is_grad():
    entry = {
        "has_restrictions": True,
        "sections": {
            "lectures": [
                {"section_id": "1", "is_cancelled": False, "notes": "This course is only open to undergraduate students."}
            ]
        },
    }
    result = _check_major_restrictions("CSCI 401", entry, {"major": "Computer Science", "classLevel": None})
    assert result.status == "fail"


def test_major_restrictions_none_when_undergrad_only_and_student_is_undergrad():
    entry = {
        "has_restrictions": True,
        "sections": {
            "lectures": [
                {"section_id": "1", "is_cancelled": False, "notes": "This course is only open to undergraduate students."}
            ]
        },
    }
    result = _check_major_restrictions("CSCI 401", entry, {"major": "Computer Science", "classLevel": "Junior"})
    assert result is None


def test_major_restrictions_warns_when_note_unparseable():
    entry = {
        "has_restrictions": True,
        "sections": {"lectures": [{"section_id": "1", "is_cancelled": False, "notes": "Some unusual restriction text."}]},
    }
    result = _check_major_restrictions("XYZ 100", entry, {"major": "Computer Science", "classLevel": "Junior"})
    assert result.status == "warning"


def test_major_restrictions_warns_when_flagged_but_no_notes():
    entry = {"has_restrictions": True, "sections": {"lectures": [{"section_id": "1", "is_cancelled": False, "notes": None}]}}
    result = _check_major_restrictions("XYZ 100", entry, {"major": "Computer Science", "classLevel": "Junior"})
    assert result.status == "warning"


# ---- time conflicts ----------------------------------------------------------

def make_catalog_entry(days, start, end, section_id="1"):
    return {"sections": {"lectures": [{"section_id": section_id, "is_cancelled": False, "days": days, "start_time": start, "end_time": end}]}}


def test_time_conflict_fails_when_only_sections_fully_overlap():
    catalog = {
        "CSCI 426": make_catalog_entry(["Wed"], "13:00", "16:20"),
        "ANTH 338": make_catalog_entry(["Mon", "Wed"], "14:00", "15:20"),
    }
    conflicts = _check_time_conflicts([("CSCI 426", None), ("ANTH 338", None)], catalog)
    assert conflicts["CSCI 426"][0].status == "fail"
    assert conflicts["ANTH 338"][0].status == "fail"


def test_time_conflict_warns_when_only_some_sections_overlap():
    catalog = {
        "A": {
            "sections": {
                "lectures": [
                    {"section_id": "a1", "is_cancelled": False, "days": ["Mon"], "start_time": "08:00", "end_time": "09:50"},
                    {"section_id": "a2", "is_cancelled": False, "days": ["Mon"], "start_time": "10:00", "end_time": "11:50"},
                ]
            }
        },
        "B": make_catalog_entry(["Mon"], "09:00", "09:50", section_id="b1"),
    }
    conflicts = _check_time_conflicts([("A", None), ("B", None)], catalog)
    assert conflicts["A"][0].status == "warning"
    assert conflicts["B"][0].status == "warning"


def test_time_conflict_absent_when_no_overlap():
    catalog = {
        "A": make_catalog_entry(["Mon"], "08:00", "09:00"),
        "B": make_catalog_entry(["Tue"], "08:00", "09:00"),
    }
    conflicts = _check_time_conflicts([("A", None), ("B", None)], catalog)
    assert conflicts == {}


def test_to_minutes_handles_malformed_input_gracefully():
    assert _to_minutes("not-a-time") is None
    assert _to_minutes(None) is None
    assert _to_minutes("TBA") is None
    assert _to_minutes("09:30") == 570


# ---- full integration --------------------------------------------------------

def test_validate_next_semester_end_to_end(planned_courses, stars_summary, course_catalog, dept_clearance):
    result = validate_next_semester(planned_courses, stars_summary, course_catalog, dept_clearance)
    assert result.overall_status == "invalid"

    by_course = {c.course: c for c in result.course_results}
    expected_status = {
        "CSCI 360": "warning",  # partial time-conflict warning with CSCI 104
        "CSCI 401": "warning",  # partial time-conflict warnings (MATH 407, ACCT 371)
        "CSCI 104": "fail",  # already completed
        "CSCI 426": "fail",  # unavoidable time conflict with ANTH 338 and ARCH 203
        "MATH 407": "fail",  # mismatched lab/discussion link code
        "ANTH 491": "warning",  # D-clearance + TBA section, no fixed time to conflict-check
        "ANTH 338": "fail",  # unavoidable time conflict with CSCI 426 and ARCH 203
        "ACCT 371": "fail",  # every section full
        "ARCH 203": "fail",  # reserved for GeoDesign/Landscape Arch, not this student's major
        "CSCI 999": "warning",  # not in catalog
    }
    for course, status in expected_status.items():
        assert by_course[course].status == status, f"{course}: expected {status}, got {by_course[course].status}"

    assert "no section that avoids conflicting with ANTH 338" in " ".join(by_course["CSCI 426"].reasons)
    assert "no section that avoids conflicting with ARCH 203" in " ".join(by_course["CSCI 426"].reasons)
    assert any("may conflict with" in r for r in by_course["CSCI 401"].reasons)
    assert any("TBA" in r for r in by_course["ANTH 491"].reasons)
    assert any("full" in r for r in by_course["ACCT 371"].reasons)
    assert any("reserved for" in r for r in by_course["ARCH 203"].reasons)
    assert any("link code" in r for r in by_course["MATH 407"].reasons)

    assert result.summary["total_units"] == 36.0
    assert any("CSCI 999" in w for w in result.summary["warnings"])
    assert any("18" in w for w in result.summary["warnings"])


def test_validate_next_semester_raises_on_bad_dept_clearance_version(planned_courses, stars_summary, course_catalog, dept_clearance):
    bad = {**dept_clearance, "_schema_version": "0.1"}
    with pytest.raises(ValueError):
        validate_next_semester(planned_courses, stars_summary, course_catalog, bad)
