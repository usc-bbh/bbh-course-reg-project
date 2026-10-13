#!/usr/bin/env python3
"""
Tests for bip.py: the golden cases pass on Vishal's examples, and deliberately
wrong encodings get caught.

    python -m unittest test_bip
"""

from __future__ import annotations

import json
import unittest

import bip
from check_bip import GOLDEN_DIR, HERE, taken_courses


def load(stem: str) -> dict:
    return json.loads((HERE / "examples" / f"{stem}.json").read_text(encoding="utf-8"))


def wrong_cases(stem: str, program: dict) -> list[str]:
    golden = json.loads((GOLDEN_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    wrong = []
    for case in golden["cases"]:
        v = bip.solve(program, taken_courses(case, golden.get("default_units", 4)))
        if v.result != case["expect"] or ("unmet" in case and sorted(v.unmet) != sorted(case["unmet"])):
            wrong.append(case["student"])
    return wrong


def econ_electives(program: dict) -> dict:
    return program["root"]["all_of"][0]["all_of"][6]


class GoldenTest(unittest.TestCase):
    def test_examples_get_every_golden_case_right(self):
        for path in sorted(GOLDEN_DIR.glob("*.json")):
            stem = json.loads(path.read_text(encoding="utf-8"))["program"]
            with self.subTest(stem):
                self.assertEqual(wrong_cases(stem, load(stem)), [])


class MutationTest(unittest.TestCase):
    """Each change makes the JSON mean something the catalogue doesn't say."""

    def assertCaught(self, stem: str, mutate) -> None:
        program = load(stem)
        mutate(program)
        self.assertTrue(wrong_cases(stem, program), "no golden case noticed the change")

    def test_econ_four_electives_becomes_three(self):
        self.assertCaught("102_economics_ba", lambda p: econ_electives(p)["thresholds"][0].update(value=3))

    def test_econ_of_which_dropped(self):
        self.assertCaught("102_economics_ba", lambda p: econ_electives(p).pop("of_which"))

    def test_econ_prefix_dropped(self):
        self.assertCaught("102_economics_ba", lambda p: econ_electives(p)["eligible_if"]["all"].pop(0))

    def test_public_policy_two_tracks(self):
        self.assertCaught("183_public_policy_bs", lambda p: p["root"]["all_of"][2].update(choose=2))

    def test_religion_root_checks_dropped(self):
        self.assertCaught("188_religion_ba", lambda p: p["root"].pop("of_which"))


class AuditTest(unittest.TestCase):
    def test_nothing_lost_in_economics(self):
        statuses = {i.status for i in bip.audit(load("102_economics_ba"))}
        self.assertNotIn("LOST", statuses)

    def test_placeholders_and_unknown_keys_reported(self):
        program = load("102_economics_ba")
        econ_electives(program)["min_grade"] = "C"  # a field the converter doesn't read
        lost = [i for i in bip.audit(program) if i.status == "LOST"]
        self.assertEqual(len(lost), 1)
        self.assertIn("min_grade", lost[0].detail)

        pp = [i for i in bip.audit(load("183_public_policy_bs")) if i.status == "LOST"]
        self.assertEqual(len(pp), 2)  # the honours GPA gate and the internship hours


if __name__ == "__main__":
    unittest.main()
