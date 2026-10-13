#!/usr/bin/env python3
"""
Tests for eligibility.py and check_taxonomy.py.

    python -m unittest test_taxonomy
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from check_taxonomy import (
    HERE,
    check_dir,
    check_object,
    check_taxonomy,
    load_schema,
    validators,
)
import bip
from eligibility import UNKNOWN, is_eligible, parse_course

CS_CORE_ELECTIVES = {"all": [{"prefix": ["CSCI"]}, {"level_min": 300, "level_max": 499}]}

ECON_ELECTIVES = {
    "family": "count",
    "eligible_if": {"all": [{"prefix": ["ECON"]}, {"level_min": 300}]},
    "thresholds": [{"count_by": "courses", "op": "min", "value": 4}],
    "of_which": [{
        "source_lines": [[21, 21]],
        "source_quote": "a minimum of two must be economics courses",
        "eligible_if": {"level_min": 400},
        "thresholds": [{"count_by": "courses", "op": "min", "value": 2}],
    }],
}

GOOD_TAXONOMY = """\
# Test taxonomy

> Of the four elective courses (300 level or above) a minimum of two must be economics
> courses at the 400 level or higher.

```json
{ "family": "count",
  "eligible_if": {"all": [ {"prefix": ["ECON"]}, {"level_min": 300} ]},
  "thresholds": [ {"count_by": "courses", "op": "min", "value": 4} ],
  "of_which": [
    { "source_lines": [[21, 21]],
      "source_quote": "a minimum of two must be economics courses",
      "eligible_if": {"level_min": 400},
      "thresholds": [ {"count_by": "courses", "op": "min", "value": 2} ] } ] }
```

> Students select four courses from the department's approved upper-division offerings.

```json
{ "family": "count",
  "eligible_if": {"all": [
    {"prefix": ["HIST"]}, {"level_min": 300},
    {"unresolved": "department's approved upper-division offerings"} ]},
  "thresholds": [ {"count_by": "courses", "op": "min", "value": 4} ] }
```

> OT 251 or EDUC 589 or PSYC 336L with PSYC 337L.

```json
{"choose": 1, "from": [
  {"family": "specific_course", "course": "OT 251"},
  {"family": "specific_course", "course": "EDUC 589"},
  {"all_of": [
    {"family": "specific_course", "course": "PSYC 336L"},
    {"family": "specific_course", "course": "PSYC 337L"}]} ]}
```

> A minimum grade of C, 2.0 is required in each course.

```json
{"source_lines": [[27, 27]], "source_quote": "A minimum grade of C, 2.0",
 "reason": "out_of_scope", "why": "Grade rule; Phase 2."}
```

> Take exactly two courses from the list.

```json
{ "family": "count",
  "eligible_if": {"courses": ["CSCI 201", "CSCI 270", "CSCI 310"]},
  "thresholds": [ {"count_by": "courses", "op": "eq", "value": 2} ] }
```
"""


class IsEligibleTest(unittest.TestCase):
    def test_vishal_cases(self):
        self.assertIs(is_eligible(CS_CORE_ELECTIVES, "CSCI 353"), True)
        self.assertIs(is_eligible(CS_CORE_ELECTIVES, "CSCI 201"), False)
        self.assertIs(is_eligible(CS_CORE_ELECTIVES, "MATH 407"), False)

    def test_level_ignores_suffix(self):
        self.assertEqual(parse_course("CSCI 103L"), ("CSCI", 103))
        self.assertIs(is_eligible({"level_max": 199}, "CSCI 103L"), True)

    def test_musc(self):
        musc = {"all": [{"prefix": ["MUSC"]}, {"level_min": 300}]}
        self.assertIs(is_eligible(musc, "MUSC 352"), True)
        self.assertIs(is_eligible(musc, "MUSC 250"), False)
        self.assertIs(is_eligible(musc, "THTR 352"), False)

    def test_course_list(self):
        self.assertIs(is_eligible({"courses": ["PPD 225", "PPD 357"]}, "PPD 357"), True)
        self.assertIs(is_eligible({"courses": ["PPD 225", "PPD 357"]}, "PPD 358"), False)

    def test_unresolved_keeps_checkable_parts(self):
        hist = {"all": [{"prefix": ["HIST"]}, {"level_min": 300},
                        {"unresolved": "department-approved offerings"}]}
        self.assertEqual(is_eligible(hist, "HIST 350"), UNKNOWN)
        self.assertIs(is_eligible(hist, "HIST 150"), False)  # fails on level, whatever the department says
        self.assertIs(is_eligible(hist, "ECON 350"), False)

    def test_three_valued_combinators(self):
        self.assertIs(is_eligible({"any": [{"prefix": ["ECON"]}, {"school": "Dornsife"}]}, "ECON 203"), True)
        self.assertEqual(is_eligible({"any": [{"prefix": ["ECON"]}, {"school": "Dornsife"}]}, "PSYC 100"), UNKNOWN)
        self.assertEqual(is_eligible({"not": {"school": "Dornsife"}}, "ECON 203"), UNKNOWN)
        self.assertIs(is_eligible({"not": {"prefix": ["ECON"]}}, "ECON 203"), False)

    def test_rejects_outside_vocabulary(self):
        with self.assertRaises(ValueError):
            is_eligible({"subject": ["ECON"]}, "ECON 203")
        with self.assertRaises(ValueError):
            is_eligible("subject MUSC, level >= 300", "MUSC 352")


class CheckTaxonomyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vals = validators(load_schema())

    def errors(self, obj, quote=None):
        return check_object(obj, self.vals, "test", quote).errors

    def test_vishal_examples_pass(self):
        results = check_dir(HERE / "examples", self.vals)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertEqual(r.errors, [], r.label)

    def test_good_taxonomy_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "taxonomy.md"
            path.write_text(GOOD_TAXONOMY, encoding="utf-8")
            results = check_taxonomy(path, self.vals)
        self.assertEqual(len(results), 5)
        self.assertEqual([r.kind for r in results], ["node", "node", "node", "unclassified", "node"])
        for r in results:
            self.assertEqual(r.errors, [], r.label)

    def test_misspelled_key_fails(self):
        broken = dict(ECON_ELECTIVES)
        broken["treshold"] = broken.pop("thresholds")
        self.assertTrue(self.errors(broken))

    def test_free_text_eligible_if_fails(self):
        broken = dict(ECON_ELECTIVES, eligible_if="subject ECON, level >= 300")
        self.assertTrue(self.errors(broken))

    def test_old_format_fails(self):
        old = {"family": "Course Selection",
               "details": {"count": {"op": "min", "value": 12}, "measure": "units",
                           "pool_rule": "subject MUSC, level >= 300"}}
        errs = self.errors(old)
        self.assertTrue(any("old family name" in e for e in errs))
        self.assertTrue(any("pool_rule" in e for e in errs))

    def test_eq_needs_exactly(self):
        leaf = {"family": "count", "eligible_if": {"courses": ["CSCI 201", "CSCI 270"]},
                "thresholds": [{"count_by": "courses", "op": "eq", "value": 2}]}
        self.assertTrue(self.errors(leaf, "Choose two courses from the list."))
        self.assertEqual(self.errors(leaf, "Take exactly two courses from the list."), [])

    def test_placeholder_fails(self):
        self.assertTrue(self.errors({"all_of": [{"family": "specific_course", "course": "MATH 125"}, "..."]}))

    def test_example_the_solver_cant_use_fails(self):
        # Simulate the converter falling behind the schema: it stops reading of_which.
        original = bip.READS["count"]
        bip.READS["count"] = original - {"of_which"}
        try:
            errs = self.errors(ECON_ELECTIVES)
        finally:
            bip.READS["count"] = original
        self.assertTrue(any("not converted to the solver" in e and "of_which" in e for e in errs), errs)

    def test_placeholder_is_only_a_warning(self):
        leaf = {"family": "sequencing", "kind": "PREREQUISITE",
                "details": {"before": ["FBE 391"], "after": ["FBE 441"]}}
        res = check_object(leaf, self.vals, "test")
        self.assertEqual(res.errors, [])
        self.assertTrue(any("placeholder" in w for w in res.warnings))

    def test_bad_course_code_inside_group_fails(self):
        nested = {"all_of": [{"choose": 1, "from": [{"family": "specific_course", "course": "math 126"}]}]}
        errs = self.errors(nested)
        self.assertTrue(any("all_of/0/from/0/course" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
