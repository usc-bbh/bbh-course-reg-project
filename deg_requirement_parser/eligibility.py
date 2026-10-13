#!/usr/bin/env python3
"""
Decide whether one course meets an `eligible_if` condition (FEEDBACK_phase1.md, T2).

    is_eligible({"all": [{"prefix": ["CSCI"]}, {"level_min": 300}]}, "CSCI 353")  -> True

Returns True, False, or "unknown". "unknown" comes from terms we have no data for
yet: `unresolved` (the catalogue gives no checkable rule), `school` (needs a
prefix-to-school table) and `ge_category` (needs a course-to-GE table).

The combinators use three-valued logic, so a known answer wins where it can:
  all: False if any part is False, else "unknown" if any part is, else True
  any: True if any part is True, else "unknown" if any part is, else False
  not: flips True and False, leaves "unknown" alone

Raises ValueError on a condition that isn't in the vocabulary, so a malformed
`eligible_if` fails loudly instead of quietly matching nothing.
"""

from __future__ import annotations

import re

UNKNOWN = "unknown"

COURSE_RE = re.compile(r"^([A-Z]{2,5}) ([0-9]{3})([A-Za-z]{0,3})$")


def parse_course(code: str) -> tuple[str, int]:
    """'CSCI 103L' -> ('CSCI', 103). The level is the course number; suffix letters don't change it."""
    m = COURSE_RE.match(code.strip())
    if not m:
        raise ValueError(f"not a course code: {code!r}")
    return m.group(1), int(m.group(2))


def _all(results: list) -> bool | str:
    if any(r is False for r in results):
        return False
    return UNKNOWN if any(r == UNKNOWN for r in results) else True


def _any(results: list) -> bool | str:
    if any(r is True for r in results):
        return True
    return UNKNOWN if any(r == UNKNOWN for r in results) else False


def is_eligible(eligible_if: dict, course_code: str) -> bool | str:
    if not isinstance(eligible_if, dict) or not eligible_if:
        raise ValueError(f"eligible_if must be a non-empty object, got {eligible_if!r}")
    prefix, level = parse_course(course_code)
    keys = set(eligible_if)

    if keys == {"all"}:
        return _all([is_eligible(c, course_code) for c in eligible_if["all"]])
    if keys == {"any"}:
        return _any([is_eligible(c, course_code) for c in eligible_if["any"]])
    if keys == {"not"}:
        inner = is_eligible(eligible_if["not"], course_code)
        return inner if inner == UNKNOWN else not inner
    if keys == {"courses"}:
        return course_code.strip() in {c.strip() for c in eligible_if["courses"]}
    if keys == {"prefix"}:
        return prefix in eligible_if["prefix"]
    if keys and keys <= {"level_min", "level_max"}:
        lo = eligible_if.get("level_min", 0)
        hi = eligible_if.get("level_max", 999)
        return lo <= level <= hi
    if keys in ({"school"}, {"ge_category"}, {"unresolved"}):
        return UNKNOWN
    raise ValueError(f"not in the eligible_if vocabulary: {eligible_if!r}")
