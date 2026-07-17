import requests
import json
import time
from datetime import datetime

headers = {"User-Agent": "Mozilla/5.0"}

TERM_CODES = {
    "20263": "Fall 2026",
    "20261": "Spring 2026",
    "20253": "Fall 2025",
    "20251": "Spring 2025",
    "20243": "Fall 2024",
    "20241": "Spring 2024",
}

LECTURE_MODES = {"Lecture", "Lecture/Lab", "Lecture/Discussion"}
LAB_MODES = {"Lab"}
DISCUSSION_MODES = {"Discussion"}
QUIZ_MODES = {"Quiz"}

def categorize_section(mode):
    if mode in LECTURE_MODES:
        return "lectures"
    elif mode in LAB_MODES:
        return "labs"
    elif mode in DISCUSSION_MODES:
        return "discussions"
    elif mode in QUIZ_MODES:
        return "quizzes"
    else:
        return "other"

def get_department_list(term_code):
    """Get the complete, authoritative list of department prefixes for a term
    directly from USC, instead of a hand-maintained guess list. Fixes the
    missing-department bug found in v4/v5 (e.g. FBE, GERO, PPD, ADNT were
    never being searched)."""
    url = f"https://classes.usc.edu/api/Search/Autocomplete?termCode={term_code}"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"  WARNING: Autocomplete failed ({response.status_code}) for term {term_code}")
            return []
        data = response.json()
        prefixes = sorted(set(c["prefix"] for c in data.get("courses", []) if c.get("prefix")))
        return prefixes
    except Exception as e:
        print(f"  WARNING: Autocomplete error for term {term_code}: {e}")
        return []

def scrape_department(dept, term_code, retries=3):
    url = f"https://classes.usc.edu/api/Search/Basic?termCode={term_code}&searchTerm={dept}"
    response = None
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            break
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt + 1}/{retries} for {dept} (term {term_code}) after error: {e}")
                time.sleep(3)
            else:
                print(f"  FAILED after {retries} attempts: {dept} (term {term_code}): {e}")
                return []
    try:
        if response is None or response.status_code != 200:
            return []
        data = response.json()
        courses = []
        for course in data.get("courses", []):
            full_name = course.get("fullCourseName", "")

            # FIX (carried from v5): USC's search API returns cross-listed /
            # loosely-related courses that don't match the queried
            # department prefix. Only keep courses that actually belong to
            # the department we asked for.
            if not full_name.startswith(dept + " "):
                continue

            raw_sections = course.get("sections", [])
            grouped = {"lectures": [], "labs": [], "discussions": [], "quizzes": [], "other": []}

            for section in raw_sections:
                schedule = section.get("schedule", [{}])
                first = schedule[0] if schedule else {}
                instructors = section.get("instructors", [{}])
                instructor_name = f"{instructors[0].get('firstName', '')} {instructors[0].get('lastName', '')}".strip() if instructors else "TBD"
                mode = section.get("rnrMode") or ""
                category = categorize_section(mode)

                parsed = {
                    "section_id": section.get("sisSectionId"),
                    "link_code": section.get("linkCode"),
                    "has_d_clearance": section.get("hasDClearance", False),
                    "notes": section.get("notes"),
                    "is_cancelled": section.get("isCancelled", False),
                    "instructor": instructor_name or "TBD",
                    "total_seats": section.get("totalSeats"),
                    "registered_seats": section.get("registeredSeats"),
                    "waitlisted_seats": section.get("waitlistedSeats") or 0,
                    "open_seats": max(0, (section.get("totalSeats") or 0) - (section.get("registeredSeats") or 0)),
                    "is_full": section.get("isFull"),
                    "mode": mode,
                    "days": first.get("days", []),
                    "start_time": first.get("startTime", ""),
                    "end_time": first.get("endTime", ""),
                    "location": first.get("location", ""),
                    "section_type": category,
                }
                grouped[category].append(parsed)

            grouped = {k: v for k, v in grouped.items() if v}
            all_sections = [s for secs in grouped.values() for s in secs]
            has_restrictions = any(s.get("notes") for s in all_sections)

            courses.append({
                "course_id": course.get("courseId"),
                "course_name": full_name,
                "class_number": course.get("classNumber"),
                "description": course.get("description"),
                "units": course.get("courseUnits", [None])[0],
                "term_code": term_code,
                "has_lab": len(grouped.get("labs", [])) > 0,
                "has_discussion": len(grouped.get("discussions", [])) > 0,
                "has_d_clearance": any(s.get("has_d_clearance") for s in all_sections),
                "has_restrictions": has_restrictions,
                "section_counts": {k: len(v) for k, v in grouped.items()},
                "sections": grouped,
            })
        return courses
    except Exception as e:
        print(f"  Error scraping {dept} for term {term_code}: {e}")
        return []

def scrape_term(term_code, term_name):
    print(f"\nScraping {term_name} ({term_code})...")

    departments = get_department_list(term_code)
    print(f"  Found {len(departments)} departments via Autocomplete")

    all_courses = []
    seen_ids = set()
    for dept in departments:
        courses = scrape_department(dept, term_code)
        new_courses = [c for c in courses if c["course_id"] not in seen_ids]
        for c in new_courses:
            seen_ids.add(c["course_id"])
        if new_courses:
            all_courses.extend(new_courses)
        time.sleep(0.15)
    print(f"  Scraped {len(all_courses)} unique courses across {len(departments)} departments")
    return all_courses

def analyze_offering_frequency(all_terms_data):
    course_terms = {}
    for term_code, courses in all_terms_data.items():
        for course in courses:
            name = course["course_name"]
            if name not in course_terms:
                course_terms[name] = []
            course_terms[name].append(term_code)

    frequency = {}
    total_terms = len(all_terms_data)
    for course_name, terms in course_terms.items():
        count = len(terms)
        if count >= total_terms - 1:
            label = "every_semester"
        elif count >= total_terms // 2:
            label = "most_semesters"
        elif count == 1:
            label = "rarely"
        else:
            label = "occasionally"
        frequency[course_name] = {
            "terms_offered": terms,
            "count": count,
            "frequency_label": label
        }
    return frequency

if __name__ == "__main__":
    all_terms_data = {}

    for term_code, term_name in TERM_CODES.items():
        courses = scrape_term(term_code, term_name)
        all_terms_data[term_code] = courses
        print(f"  Total: {len(courses)} courses for {term_name}")

    print("\nAnalyzing offering frequency...")
    frequency = analyze_offering_frequency(all_terms_data)

    output = {
        "generated_at": datetime.now().isoformat(),
        "schema_version": "6.0",
        "terms": TERM_CODES,
        "terms_data": all_terms_data,
        "offering_frequency": frequency,
    }

    with open("bbh_schedule_data_v6.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone! Saved to bbh_schedule_data_v6.json")
    print(f"Total courses: {sum(len(v) for v in all_terms_data.values())}")
    print(f"Unique courses: {len(frequency)}")

    d_clearance = sum(1 for courses in all_terms_data.values() for c in courses if c.get("has_d_clearance"))
    restrictions = sum(1 for courses in all_terms_data.values() for c in courses if c.get("has_restrictions"))
    print(f"Courses with D-clearance: {d_clearance}")
    print(f"Courses with restriction notes: {restrictions}")
