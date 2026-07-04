"""Module 4B: next-semester validator.

Checks a student's planned courses against their STARS report and the course
catalog. Prereq and D-clearance data are inconsistent/free-text in the current
sources, so those checks surface as warnings with the raw source text rather
than computed pass/fail.
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


def validate_next_semester(planned_courses: list[str], stars_report: dict, course_catalog: dict) -> ValidationResult:
    dept_clearance_by_prefix = _load_dept_clearance_by_prefix()
    catalog = {_normalize_code(code): entry for code, entry in course_catalog.get("courses", course_catalog).items()}

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
        ]
        results = [r for r in checks if r]

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
