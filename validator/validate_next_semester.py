"""Module 4B: next-semester validator.

Checks a student's planned courses against a STARS summary, the course
catalog (Agastya's schedule scrape), and USC department D-clearance rules.

Each entry in `planned_courses` may be a plain course code string, e.g.
"CSCI 104", or a dict naming specific chosen sections, e.g.
{"course": "CSCI 104", "sections": ["29903", "30119"]}. When sections are
given, seat availability, time conflicts, and lab/discussion pairing are
checked against exactly those sections. When they're not, those checks fall
back to "is there at least one viable choice" / "is every section full"
across all of the course's sections.

Prereqs and major restrictions are parsed out of free-text catalog fields on
a best-effort basis (course codes, GPA thresholds, "reserved for X" /
"not available for X majors" / "only open to undergrad/grad" phrasing).
When a description doesn't match a recognized pattern, it's surfaced as an
unverified warning instead of silently dropped or blindly passed.

Time conflict is evaluated per pair of planned courses: a course contributes
all of its considered sections as options. A pair is only a hard `fail` when
every option combination overlaps (no viable choice avoids it); if only some
combinations overlap, it's a `warning`. When a course has multiple selected
sections (e.g. lecture + lab both chosen), they're treated as alternative
options for this comparison rather than a simultaneous commitment, which can
under-flag a conflict that only comes from one of the selected sections. TBA
or malformed section times are skipped for conflict purposes but surfaced as
a separate warning rather than silently dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MAX_RECOMMENDED_UNITS = 18
CLASS_LEVEL_ORDER = {"Freshman": 1, "Sophomore": 2, "Junior": 3, "Senior": 4}
EXPECTED_DEPT_CLEARANCE_SCHEMA_VERSION = "1.4"


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
    """Parses "HH:MM" to minutes since midnight; returns None for TBA/missing/malformed input."""
    if not time_str or time_str == "TBA":
        return None
    try:
        hours, minutes = time_str.split(":")
        return int(hours) * 60 + int(minutes)
    except (ValueError, AttributeError):
        return None


def _parse_planned_entry(entry: str | dict) -> tuple[str, set[str] | None]:
    """Splits a planned_courses item into (course_code, selected_section_ids or None)."""
    if isinstance(entry, dict):
        sections = entry.get("sections")
        return entry["course"], set(sections) if sections else None
    return entry, None


def _all_sections(catalog_entry: dict, selected_section_ids: set[str] | None = None) -> list[dict]:
    """Every non-cancelled section for a course, optionally filtered to a specific selection."""
    sections = [
        section
        for group in catalog_entry.get("sections", {}).values()
        for section in group
        if not section.get("is_cancelled")
    ]
    if selected_section_ids is not None:
        sections = [s for s in sections if s["section_id"] in selected_section_ids]
    return sections


def _dept_clearance_by_prefix(dept_clearance: dict) -> dict:
    """Indexes dept_clearance.json by course prefix, expanding school_fallback entries."""
    version = dept_clearance.get("_schema_version")
    if version != EXPECTED_DEPT_CLEARANCE_SCHEMA_VERSION:
        raise ValueError(
            f"dept_clearance schema version {version!r} does not match the expected "
            f"{EXPECTED_DEPT_CLEARANCE_SCHEMA_VERSION!r} -- refusing to guess at an unfamiliar shape."
        )
    by_prefix = {}
    for entry in dept_clearance["departments"]:
        if entry.get("type") == "school_fallback":
            for prefix in entry.get("covers_prefixes", []):
                by_prefix.setdefault(prefix, entry)
        else:
            by_prefix[entry["dept_code"]] = entry
    return by_prefix


def _check_already_taken(course: str, stars_summary: dict) -> CourseResult | None:
    """Fails if already completed, warns if already in progress this term."""
    norm = _normalize_code(course)
    completed = {_normalize_code(c["code"]) for c in stars_summary.get("completedCourses", [])}
    in_progress = {_normalize_code(c["code"]) for c in stars_summary.get("inProgressCourses", [])}
    if norm in completed:
        return CourseResult(course, "fail", [f"{norm} is already completed."])
    if norm in in_progress:
        return CourseResult(course, "warning", [f"{norm} is already in progress this term."])
    return None


def _check_standing(course: str, stars_summary: dict) -> CourseResult | None:
    """Warns if a 400+ course is planned by a Freshman/Sophomore. Not a hard fail: USC's own
    glossary says 300/400-level is "primarily for" juniors/seniors as guidance, not a blanket
    rule -- actual enforcement is per-course (e.g. some courses require junior standing
    themselves), which this validator can't see."""
    number = _course_number(course)
    class_level = stars_summary.get("classLevel")
    if number is None or class_level not in CLASS_LEVEL_ORDER:
        return None
    if number >= 400 and CLASS_LEVEL_ORDER[class_level] < 3:
        return CourseResult(
            course,
            "warning",
            [f"{class_level}s may not be eligible for some 400+ level courses (current standing: {class_level}) — check the specific course's requirements."],
        )
    return None


def _check_d_clearance(course: str, catalog_entry: dict | None, dept_clearance_by_prefix: dict) -> CourseResult | None:
    """Warns (never a hard fail) when the catalog marks this course as requiring D-clearance."""
    if not catalog_entry or not catalog_entry.get("has_d_clearance"):
        return None
    reasons = [f"{course} requires departmental clearance (D-clearance) to enroll this term."]
    dept = dept_clearance_by_prefix.get(_course_prefix(course))
    if dept:
        reasons.append(dept["clearance_required_for"])
        reasons.append(f"How to get clearance: {dept['how_to_get_clearance']}")
    return CourseResult(course, "warning", reasons)


def _check_prereq(course: str, catalog_entry: dict | None, stars_summary: dict) -> CourseResult | None:
    """Best-effort: extracts a GPA threshold and/or course codes from the description and verifies
    them against the STARS summary. Falls back to an unverified warning when nothing recognizable
    is found (e.g. "consent of instructor", unit-count-based requirements)."""
    if not catalog_entry:
        return None
    description = catalog_entry.get("description") or ""
    if not re.search(r"prereq|requisite", description, re.IGNORECASE):
        return None

    completed = {_normalize_code(c["code"]) for c in stars_summary.get("completedCourses", [])}
    gpa = stars_summary.get("gpa")

    reasons = []
    status = "pass"
    matched_any = False

    gpa_match = re.search(r"([\d.]+)\s*gpa", description, re.IGNORECASE)
    if gpa_match:
        matched_any = True
        required_gpa = float(gpa_match.group(1))
        if gpa is None or gpa < required_gpa:
            status = "fail"
            reasons.append(f"{course} requires a {required_gpa} GPA minimum (yours: {gpa}).")

    required_codes = {
        f"{dept.upper()} {num.upper()}" for dept, num in re.findall(r"\b([A-Z]{2,4})\s?(\d{3}[A-Za-z]?)\b", description)
    }
    required_codes.discard(_normalize_code(course))
    if required_codes:
        matched_any = True
        missing = sorted(required_codes - completed)
        if missing:
            status = "fail"
            reasons.append(f"{course} is missing prerequisite(s): {', '.join(missing)}.")

    if not matched_any:
        status = "warning"
        reasons.append(f"Prerequisite note (unverified): {description.strip()}")

    if not reasons:
        return None
    return CourseResult(course, status, reasons)


def _check_in_catalog(course: str, catalog: dict) -> CourseResult | None:
    """Warns when a planned course code has no match in this term's catalog."""
    if _normalize_code(course) not in catalog:
        return CourseResult(course, "warning", [f"{course} was not found in the course catalog for this term."])
    return None


def _check_seat_availability(course: str, catalog_entry: dict | None, selected_section_ids: set[str] | None) -> CourseResult | None:
    """Fails if the selected section(s) are full, or (with no selection) if every section is full."""
    if not catalog_entry:
        return None
    sections = _all_sections(catalog_entry, selected_section_ids)
    if not sections:
        return None
    full = [s for s in sections if s.get("is_full")]
    if selected_section_ids is not None:
        if full:
            ids = ", ".join(s["section_id"] for s in full)
            return CourseResult(course, "fail", [f"Selected section(s) {ids} of {course} are full."])
        return None
    if len(full) == len(sections):
        return CourseResult(course, "fail", [f"Every section of {course} is full for this term."])
    return None


def _check_lab_discussion_pairing(course: str, catalog_entry: dict | None, selected_section_ids: set[str] | None) -> CourseResult | None:
    """With sections selected: verifies a required lab/discussion was chosen and shares the lecture's
    link code. Without a selection: a reminder warning, since there's nothing to verify yet."""
    if not catalog_entry:
        return None
    required_groups = [group for group, key in [("labs", "has_lab"), ("discussions", "has_discussion")] if catalog_entry.get(key)]
    if not required_groups:
        return None

    if selected_section_ids is None:
        labels = [g[:-1] for g in required_groups]
        return CourseResult(
            course,
            "warning",
            [f"{course} requires a linked {'/'.join(labels)} section — register for a matching section (same link code) in addition to the lecture."],
        )

    sections_by_group = {
        group: [s for s in secs if s["section_id"] in selected_section_ids]
        for group, secs in catalog_entry.get("sections", {}).items()
    }
    lecture_selected = sections_by_group.get("lectures", [])
    lecture_link = lecture_selected[0].get("link_code") if lecture_selected else None

    reasons = []
    for group in required_groups:
        label = group[:-1]
        selected_in_group = sections_by_group.get(group, [])
        if not selected_in_group:
            reasons.append(f"{course} requires a {label} section, but none was selected.")
        elif lecture_link is not None and any(s.get("link_code") != lecture_link for s in selected_in_group):
            reasons.append(f"{course}'s selected {label} section doesn't share a link code with the selected lecture.")

    if not reasons:
        return None
    return CourseResult(course, "fail", reasons)


def _check_major_restrictions(course: str, catalog_entry: dict | None, stars_summary: dict) -> CourseResult | None:
    """Best-effort: matches "reserved for X" / "not available for X majors" / "only open to
    undergrad/grad" phrasing in section notes against the student's declared major and class
    level. Unrecognized restriction text is surfaced as an unverified warning."""
    if not catalog_entry or not catalog_entry.get("has_restrictions"):
        return None
    notes = list(dict.fromkeys(s["notes"] for s in _all_sections(catalog_entry) if s.get("notes")))
    if not notes:
        return CourseResult(
            course, "warning", [f"{course} has registration restrictions — check section notes on WebReg to confirm eligibility."]
        )

    student_major = (stars_summary.get("major") or "").lower()
    is_undergrad = stars_summary.get("classLevel") in CLASS_LEVEL_ORDER

    reasons = []
    status = "pass"

    for note in notes:
        matched = False

        reserved = re.search(r"reserved for (?:students )?(?:in )?(?:the )?(.+)", note, re.IGNORECASE)
        if reserved:
            matched = True
            remainder = reserved.group(1)
            # Stop at the first sentence-ending period, skipping abbreviations like "B.S."
            # (where the char before the period is itself an uppercase letter).
            end = len(remainder)
            for boundary in re.finditer(r"\.(?:\s|$)", remainder):
                preceding = remainder[boundary.start() - 1 : boundary.start()]
                if preceding and not preceding.isupper():
                    end = boundary.start()
                    break
            allowed = remainder[:end]
            allowed_text = allowed.lower()
            major_words = [w for w in student_major.split() if len(w) > 3]
            if student_major and student_major not in allowed_text and not any(w in allowed_text for w in major_words):
                status = "fail"
                reasons.append(f"{course} is reserved for: {allowed.strip()} (unverified match against your declared major).")

        for excluded in re.findall(r"not available for ([A-Za-z][A-Za-z &]*?) majors", note, re.IGNORECASE):
            matched = True
            excluded_norm = excluded.strip().lower()
            if student_major and (excluded_norm in student_major or student_major in excluded_norm):
                status = "fail"
                reasons.append(f"{course} is not available for {excluded.strip()} majors.")

        if re.search(r"only open to undergraduate students", note, re.IGNORECASE):
            matched = True
            if not is_undergrad:
                status = "fail"
                reasons.append(f"{course} is only open to undergraduate students.")

        if re.search(r"only open to graduate students", note, re.IGNORECASE):
            matched = True
            if is_undergrad:
                status = "fail"
                reasons.append(f"{course} is only open to graduate students.")

        if not matched:
            if status != "fail":
                status = "warning"
            reasons.append(f"Registration restriction (unverified): {note}")

    if not reasons:
        return None
    return CourseResult(course, status, reasons)


def _section_time_options(
    catalog_entry: dict | None, selected_section_ids: set[str] | None
) -> tuple[list[tuple[frozenset, int, int]], list[str]]:
    """Returns (usable time options, section_ids skipped for TBA/malformed times)."""
    if not catalog_entry:
        return [], []
    options = []
    unresolved = []
    for section in _all_sections(catalog_entry, selected_section_ids):
        days = frozenset(section.get("days") or [])
        start = _to_minutes(section.get("start_time"))
        end = _to_minutes(section.get("end_time"))
        if not days or start is None or end is None:
            unresolved.append(section["section_id"])
            continue
        options.append((days, start, end))
    return options, unresolved


def _sections_overlap(a: tuple[frozenset, int, int], b: tuple[frozenset, int, int]) -> bool:
    days_a, start_a, end_a = a
    days_b, start_b, end_b = b
    return bool(days_a & days_b) and start_a < end_b and start_b < end_a


def _check_unresolved_time_sections(course: str, unresolved: list[str]) -> CourseResult | None:
    """Warns (instead of silently skipping) when a considered section has a TBA/malformed time."""
    if not unresolved:
        return None
    ids = ", ".join(unresolved)
    return CourseResult(
        course, "warning", [f"{course} section(s) {ids} have a TBA/unlisted meeting time and couldn't be checked for time conflicts."]
    )


def _check_time_conflicts(parsed_entries: list[tuple[str, set[str] | None]], catalog: dict) -> dict[str, list[CourseResult]]:
    """Pairwise: fails when every section-combination between two courses overlaps (no viable
    choice avoids it), warns when only some combinations do."""
    results: dict[str, list[CourseResult]] = {}
    options_by_course = {
        course: _section_time_options(catalog.get(_normalize_code(course)), selected)[0] for course, selected in parsed_entries
    }
    courses = [course for course, _ in parsed_entries]

    for i, course_a in enumerate(courses):
        options_a = options_by_course[course_a]
        if not options_a:
            continue
        for course_b in courses[i + 1 :]:
            options_b = options_by_course[course_b]
            if not options_b:
                continue
            combos = [(a, b) for a in options_a for b in options_b]
            overlapping = [c for c in combos if _sections_overlap(*c)]
            if not overlapping:
                continue
            status = "fail" if len(overlapping) == len(combos) else "warning"
            phrase = "has no section that avoids conflicting with" if status == "fail" else "may conflict with, depending on section choice,"
            results.setdefault(course_a, []).append(CourseResult(course_a, status, [f"{course_a} {phrase} {course_b}."]))
            results.setdefault(course_b, []).append(CourseResult(course_b, status, [f"{course_b} {phrase} {course_a}."]))

    return results


def validate_next_semester(
    planned_courses: list[str | dict], stars_summary: dict, course_catalog: dict, dept_clearance: dict
) -> ValidationResult:
    dept_clearance_by_prefix = _dept_clearance_by_prefix(dept_clearance)
    catalog = {_normalize_code(code): entry for code, entry in course_catalog.get("courses", course_catalog).items()}

    parsed_entries = [_parse_planned_entry(entry) for entry in planned_courses]
    time_conflicts = _check_time_conflicts(parsed_entries, catalog)

    course_results = []
    total_units = 0.0
    missing_from_catalog = []

    for course, selected_section_ids in parsed_entries:
        catalog_entry = catalog.get(_normalize_code(course))
        _, unresolved_time_sections = _section_time_options(catalog_entry, selected_section_ids)

        checks = [
            _check_already_taken(course, stars_summary),
            _check_standing(course, stars_summary),
            _check_d_clearance(course, catalog_entry, dept_clearance_by_prefix),
            _check_prereq(course, catalog_entry, stars_summary),
            _check_in_catalog(course, catalog),
            _check_seat_availability(course, catalog_entry, selected_section_ids),
            _check_lab_discussion_pairing(course, catalog_entry, selected_section_ids),
            _check_major_restrictions(course, catalog_entry, stars_summary),
            _check_unresolved_time_sections(course, unresolved_time_sections),
            *time_conflicts.get(course, []),
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
        else:
            missing_from_catalog.append(course)

        course_results.append(CourseResult(course, status, reasons))

    summary_warnings = []
    if total_units > MAX_RECOMMENDED_UNITS:
        summary_warnings.append(
            f"Planned load is {total_units} units, above the recommended max of {MAX_RECOMMENDED_UNITS}."
        )
    if missing_from_catalog:
        summary_warnings.append(
            f"total_units excludes {len(missing_from_catalog)} course(s) not found in the catalog: {', '.join(missing_from_catalog)}."
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
    stars_summary = json.loads((fixtures / "mock_stars_report.json").read_text())
    planned = json.loads((fixtures / "mock_planned_courses.json").read_text())
    catalog = json.loads((fixtures / "mock_course_catalog.json").read_text())
    dept_clearance = json.loads((REPO_ROOT / "dept_clearance.json").read_text())

    result = validate_next_semester(planned["planned_courses"], stars_summary, catalog, dept_clearance)
    print(json.dumps(asdict(result), indent=2))
