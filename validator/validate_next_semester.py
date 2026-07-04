"""Module 4B: next-semester validator.

Checks a student's planned courses against their STARS report and the course
catalog (Agastya's schedule scrape). Prereq, D-clearance, and major-restriction
details are inconsistent/free-text in the current sources, so those checks
surface as warnings with the raw source text rather than computed pass/fail.

Time conflict is checked per pair of planned courses across ALL of each
course's sections (lecture, lab, discussion, quiz) as if any one of them could
be picked independently. It does not model "this lecture requires that
specific paired discussion," so it can miss conflicts that only show up once
a specific section combination is locked in.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEPT_CLEARANCE_PATH = REPO_ROOT / "dept_clearance.json"

MAX_RECOMMENDED_UNITS = 18
CLASS_LEVEL_ORDER = {"Freshman": 1, "Sophomore": 2, "Junior": 3, "Senior": 4}


@dataclass
class CourseResult:
    course: str
    status: str  # "pass" | "fail" | "warning"
    reasons: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    overall_status: str  # "valid" | "invalid" | "warning"
    course_results: list[CourseResult]
    summary: dict


def _normalize_code(code: str) -> str:
    match = re.match(r"([A-Za-z]+)\s*(\d+[A-Za-z]?)", code.strip())
    if not match:
        return code.strip().upper()
    return f"{match.group(1).upper()} {match.group(2).upper()}"


def _course_prefix(code: str) -> str:
    match = re.match(r"[A-Za-z]+", code.strip())
    return match.group(0).upper() if match else code.strip().upper()


def _course_number(code: str) -> int | None:
    match = re.search(r"\d+", code)
    return int(match.group(0)) if match else None


def _to_minutes(time_str: str | None) -> int | None:
    if not time_str or time_str == "TBA":
        return None
    hours, minutes = time_str.split(":")
    return int(hours) * 60 + int(minutes)


def _all_sections(catalog_entry: dict) -> list[dict]:
    return [
        section
        for group in catalog_entry.get("sections", {}).values()
        for section in group
        if not section.get("is_cancelled")
    ]


def _load_dept_clearance_by_prefix() -> dict:
    with open(DEPT_CLEARANCE_PATH) as f:
        data = json.load(f)
    by_prefix = {}
    for entry in data["departments"]:
        if entry.get("type") == "school_fallback":
            for prefix in entry.get("covers_prefixes", []):
                by_prefix.setdefault(prefix, entry)
        else:
            by_prefix[entry["dept_code"]] = entry
    return by_prefix


def _check_already_taken(course: str, stars_report: dict) -> CourseResult | None:
    norm = _normalize_code(course)
    completed = {_normalize_code(c["code"]) for c in stars_report.get("completedCourses", [])}
    in_progress = {_normalize_code(c["code"]) for c in stars_report.get("inProgressCourses", [])}
    if norm in completed:
        return CourseResult(course, "fail", [f"{norm} is already completed."])
    if norm in in_progress:
        return CourseResult(course, "warning", [f"{norm} is already in progress this term."])
    return None


def _check_standing(course: str, stars_report: dict) -> CourseResult | None:
    number = _course_number(course)
    class_level = stars_report.get("classLevel")
    if number is None or class_level not in CLASS_LEVEL_ORDER:
        return None
    if number >= 400 and CLASS_LEVEL_ORDER[class_level] < 3:
        return CourseResult(
            course,
            "fail",
            [f"{class_level}s are not eligible for 400+ level courses (current standing: {class_level})."],
        )
    return None


def _check_d_clearance(course: str, catalog_entry: dict | None, dept_clearance_by_prefix: dict) -> CourseResult | None:
    if not catalog_entry or not catalog_entry.get("has_d_clearance"):
        return None
    reasons = [f"{course} requires departmental clearance (D-clearance) to enroll this term."]
    dept = dept_clearance_by_prefix.get(_course_prefix(course))
    if dept:
        reasons.append(dept["clearance_required_for"])
        reasons.append(f"How to get clearance: {dept['how_to_get_clearance']}")
    return CourseResult(course, "warning", reasons)


def _check_prereq_note(course: str, catalog_entry: dict | None) -> CourseResult | None:
    if not catalog_entry:
        return None
    description = catalog_entry.get("description") or ""
    if re.search(r"prereq|requisite", description, re.IGNORECASE):
        return CourseResult(course, "warning", [f"Prerequisite note (unverified): {description.strip()}"])
    return None


def _check_in_catalog(course: str, catalog: dict) -> CourseResult | None:
    if _normalize_code(course) not in catalog:
        return CourseResult(course, "warning", [f"{course} was not found in the course catalog for this term."])
    return None


def _check_seat_availability(course: str, catalog_entry: dict | None) -> CourseResult | None:
    if not catalog_entry:
        return None
    sections = _all_sections(catalog_entry)
    if sections and all(s.get("is_full") for s in sections):
        return CourseResult(course, "fail", [f"Every section of {course} is full for this term."])
    return None


def _check_lab_discussion_pairing(course: str, catalog_entry: dict | None) -> CourseResult | None:
    if not catalog_entry:
        return None
    required = [label for label, key in [("lab", "has_lab"), ("discussion", "has_discussion")] if catalog_entry.get(key)]
    if not required:
        return None
    return CourseResult(
        course,
        "warning",
        [f"{course} requires a linked {'/'.join(required)} section — register for a matching section (same link code) in addition to the lecture."],
    )


def _check_major_restrictions(course: str, catalog_entry: dict | None) -> CourseResult | None:
    if not catalog_entry or not catalog_entry.get("has_restrictions"):
        return None
    notes = list(dict.fromkeys(s["notes"] for s in _all_sections(catalog_entry) if s.get("notes")))
    if notes:
        return CourseResult(course, "warning", [f"Registration restriction (unverified): {note}" for note in notes])
    return CourseResult(
        course, "warning", [f"{course} has registration restrictions — check section notes on WebReg to confirm eligibility."]
    )


def _section_time_options(catalog_entry: dict | None) -> list[tuple[frozenset, int, int]]:
    if not catalog_entry:
        return []
    options = []
    for section in _all_sections(catalog_entry):
        days = frozenset(section.get("days") or [])
        start = _to_minutes(section.get("start_time"))
        end = _to_minutes(section.get("end_time"))
        if not days or start is None or end is None:
            continue
        options.append((days, start, end))
    return options


def _sections_overlap(a: tuple[frozenset, int, int], b: tuple[frozenset, int, int]) -> bool:
    days_a, start_a, end_a = a
    days_b, start_b, end_b = b
    return bool(days_a & days_b) and start_a < end_b and start_b < end_a


def _check_time_conflicts(planned_courses: list[str], catalog: dict) -> dict[str, list[str]]:
    """Returns {course: [conflict reasons]} for pairs with no non-overlapping section combination."""
    conflicts: dict[str, list[str]] = {}
    options_by_course = {course: _section_time_options(catalog.get(_normalize_code(course))) for course in planned_courses}

    for i, course_a in enumerate(planned_courses):
        options_a = options_by_course[course_a]
        if not options_a:
            continue
        for course_b in planned_courses[i + 1 :]:
            options_b = options_by_course[course_b]
            if not options_b:
                continue
            if all(_sections_overlap(a, b) for a in options_a for b in options_b):
                conflicts.setdefault(course_a, []).append(
                    f"{course_a} has no section that avoids conflicting with {course_b}."
                )
                conflicts.setdefault(course_b, []).append(
                    f"{course_b} has no section that avoids conflicting with {course_a}."
                )

    return conflicts


def validate_next_semester(planned_courses: list[str], stars_report: dict, course_catalog: dict) -> ValidationResult:
    dept_clearance_by_prefix = _load_dept_clearance_by_prefix()
    catalog = {_normalize_code(code): entry for code, entry in course_catalog.get("courses", course_catalog).items()}
    time_conflicts = _check_time_conflicts(planned_courses, catalog)

    course_results = []
    total_units = 0.0

    for course in planned_courses:
        catalog_entry = catalog.get(_normalize_code(course))
        checks = [
            _check_already_taken(course, stars_report),
            _check_standing(course, stars_report),
            _check_d_clearance(course, catalog_entry, dept_clearance_by_prefix),
            _check_prereq_note(course, catalog_entry),
            _check_in_catalog(course, catalog),
            _check_seat_availability(course, catalog_entry),
            _check_lab_discussion_pairing(course, catalog_entry),
            _check_major_restrictions(course, catalog_entry),
        ]
        results = [r for r in checks if r]
        if course in time_conflicts:
            results.append(CourseResult(course, "fail", time_conflicts[course]))

        reasons = [reason for r in results for reason in r.reasons]
        if any(r.status == "fail" for r in results):
            status = "fail"
        elif any(r.status == "warning" for r in results):
            status = "warning"
        else:
            status = "pass"

        if catalog_entry:
            total_units += catalog_entry.get("units", 0)

        course_results.append(CourseResult(course, status, reasons))

    summary_warnings = []
    if total_units > MAX_RECOMMENDED_UNITS:
        summary_warnings.append(
            f"Planned load is {total_units} units, above the recommended max of {MAX_RECOMMENDED_UNITS}."
        )

    if any(c.status == "fail" for c in course_results):
        overall_status = "invalid"
    elif summary_warnings or any(c.status == "warning" for c in course_results):
        overall_status = "warning"
    else:
        overall_status = "valid"

    return ValidationResult(
        overall_status=overall_status,
        course_results=course_results,
        summary={"total_units": total_units, "warnings": summary_warnings},
    )


if __name__ == "__main__":
    fixtures = Path(__file__).parent / "test" / "fixtures"
    stars_report = json.loads((fixtures / "mock_stars_report.json").read_text())
    planned = json.loads((fixtures / "mock_planned_courses.json").read_text())
    catalog = json.loads((fixtures / "mock_course_catalog.json").read_text())

    result = validate_next_semester(planned["planned_courses"], stars_report, catalog)
    print(json.dumps(asdict(result), indent=2))
