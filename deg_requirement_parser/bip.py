#!/usr/bin/env python3
"""
Turn a requirement JSON into a binary integer program (BIP), and say exactly
what didn't make it in. Proof of concept.

Two questions, two functions:

  audit(program)          Does the JSON carry enough information for a solver?
                          Lists every requirement in the program and whether it
                          became BIP constraints, so nothing is lost silently.

  solve(program, taken)   Does this student meet the requirements? Builds the
                          BIP for their courses and asks the solver whether a
                          valid assignment exists. Used to run golden cases.

The model (one program, one student)

  x[c, l]  1 if taken course c fills a slot in leaf l (only where c is eligible)
  y[n]     1 if node n is active (counted toward the degree)

  root               y[root] = 1
  all_of             y[child] >= y[node] for every child
  choose N           sum of y[child] >= N * y[node]
  any child          y[child] <= y[parent], so an inactive branch uses no courses
  specific_course    x[course, l] = y[l], or y[l] = 0 if it wasn't taken
  count              x[c, l] <= y[l]; each threshold over sum of x[c, l]
                     (min: >= value * y[l]; max: <= value; eq: both)
  one-slot rule      for each course, sum over leaves of x[c, l] <= 1
  of_which check     same thresholds, over the x's in the node's subtree
                     whose course passes the check's eligible_if

  count_by "units" weights each x by the course's units, "courses" by 1, and
  "departments" adds d[p, l] = 1 if any course with prefix p is used
  (prefix stands in for department; taxonomy_open_questions.md Q5).

What can't be converted, and so is reported rather than dropped
  - course_reuse, sequencing, manual_review leaves: Phase 1 placeholders with
    free-form details. Treated as met; listed as LOST.
  - unresolved / school / ge_category in an eligible_if: converted, but the
    answer depends on missing data. The student is solved twice (unknown
    courses eligible, then not). If the two answers differ, the verdict is
    "unknown".
  - any key the converter doesn't read: LOST. If the schema grows a field
    (grades, say) before this file learns it, the audit says so.
  - unclassified entries: outside the tree by design; counted by reason.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import pulp

from eligibility import UNKNOWN, is_eligible

PLACEHOLDER_FAMILIES = {"course_reuse", "sequencing", "manual_review"}
UNKNOWN_TERMS = {"unresolved", "school", "ge_category"}

# Keys the converter reads, per kind of object. Anything else is reported LOST.
META = {"id", "description", "confidence", "note", "source_lines", "source_quote"}
READS = {
    "all_of": {"all_of", "of_which"},
    "choose": {"choose", "from", "of_which"},
    "specific_course": {"family", "course", "of_which"},
    "count": {"family", "eligible_if", "thresholds", "of_which"},
    "check": {"eligible_if", "thresholds"},
    "threshold": {"count_by", "op", "value"},
}


# --- Audit -------------------------------------------------------------------

@dataclass
class AuditItem:
    path: str
    what: str
    status: str  # "converted" | "needs data" | "LOST"
    detail: str = ""


def node_kind(node: dict) -> str:
    if "all_of" in node:
        return "all_of"
    if "choose" in node:
        return "choose"
    return node.get("family", "?")


def label(node: dict, path: str) -> str:
    if node.get("id"):
        return node["id"]
    if node.get("family") == "specific_course":
        return node["course"]
    return path


def unknown_terms(cond) -> set[str]:
    found = set()
    if isinstance(cond, dict):
        for k, v in cond.items():
            if k in UNKNOWN_TERMS:
                found.add(k)
            found |= unknown_terms(v)
    elif isinstance(cond, list):
        for v in cond:
            found |= unknown_terms(v)
    return found


def _unread(obj: dict, kind: str) -> list[str]:
    return sorted(set(obj) - READS[kind] - META)


def audit(program: dict) -> list[AuditItem]:
    items: list[AuditItem] = []

    def visit_check(check: dict, path: str) -> None:
        extra = _unread(check, "check")
        for t in check.get("thresholds", []):
            extra += _unread(t, "threshold")
        unknown = unknown_terms(check.get("eligible_if"))
        if extra:
            items.append(AuditItem(path, "of_which check", "LOST", f"unread keys {extra}"))
        elif unknown:
            items.append(AuditItem(path, "of_which check", "needs data", f"uses {sorted(unknown)}"))
        else:
            items.append(AuditItem(path, "of_which check", "converted"))

    def visit(node: dict, path: str) -> None:
        kind = node_kind(node)
        what = f"{kind} {label(node, path)}"
        if kind in PLACEHOLDER_FAMILIES:
            items.append(AuditItem(path, what, "LOST",
                                   f"Phase 1 placeholder ({node.get('kind')}), treated as met"))
        elif kind not in READS:
            items.append(AuditItem(path, what, "LOST", "not a node the converter knows"))
        else:
            extra = _unread(node, kind)
            for t in node.get("thresholds", []):
                extra += _unread(t, "threshold")
            unknown = unknown_terms(node.get("eligible_if"))
            if extra:
                items.append(AuditItem(path, what, "LOST", f"unread keys {extra}"))
            elif unknown:
                items.append(AuditItem(path, what, "needs data", f"uses {sorted(unknown)}"))
            else:
                items.append(AuditItem(path, what, "converted"))
        for i, check in enumerate(node.get("of_which", [])):
            visit_check(check, f"{path}/of_which/{i}")
        for key in ("all_of", "from"):
            for i, child in enumerate(node.get(key, [])):
                visit(child, f"{path}/{key}/{i}")

    visit(program["root"], "root")
    for i, u in enumerate(program.get("unclassified", [])):
        items.append(AuditItem(f"unclassified/{i}", f"unclassified ({u.get('reason')})", "outside tree",
                               u.get("source_quote", "")))
    return items


# --- Solve -------------------------------------------------------------------

@dataclass
class Verdict:
    result: str  # "pass" | "fail" | "unknown"
    assignment: dict[str, list[str]] = field(default_factory=dict)  # leaf label -> courses used
    unmet: list[str] = field(default_factory=list)  # top-level nodes that fail even on their own


class _Builder:
    def __init__(self, taken: dict[str, float], unknown_as: bool):
        self.taken = taken
        self.unknown_as = unknown_as
        self.prob = pulp.LpProblem("degree", pulp.LpMinimize)
        self.n = itertools.count()
        self.slots: dict[str, list] = {c: [] for c in taken}  # course -> x vars using it
        self.leaf_x: dict[str, dict[str, pulp.LpVariable]] = {}  # leaf label -> {course: x}

    def var(self, prefix: str) -> pulp.LpVariable:
        return pulp.LpVariable(f"{prefix}_{next(self.n)}", cat="Binary")

    def eligible(self, cond: dict | None, course: str) -> bool:
        if cond is None:
            return True
        r = is_eligible(cond, course)
        return self.unknown_as if r == UNKNOWN else r

    def weighted(self, xs: dict[str, pulp.LpVariable], count_by: str, tag: str):
        """The quantity a threshold compares: a linear expression over the x's."""
        if count_by == "courses":
            return pulp.lpSum(xs.values())
        if count_by == "units":
            return pulp.lpSum(self.taken[c] * x for c, x in xs.items())
        if count_by == "departments":
            ds = []
            for prefix in {c.split()[0] for c in xs}:
                d = self.var(f"dept_{tag}")
                members = [x for c, x in xs.items() if c.split()[0] == prefix]
                self.prob += d <= pulp.lpSum(members)
                for x in members:
                    self.prob += d >= x
                ds.append(d)
            return pulp.lpSum(ds)
        raise ValueError(f"unknown count_by {count_by!r}")

    def thresholds(self, xs: dict, thresholds: list[dict], y, tag: str) -> None:
        for t in thresholds:
            total = self.weighted(xs, t["count_by"], tag)
            if t["op"] in ("min", "eq"):
                self.prob += total >= t["value"] * y
            if t["op"] in ("max", "eq"):
                self.prob += total <= t["value"]

    def node(self, node: dict, path: str, parent_y=None) -> tuple[pulp.LpVariable, dict]:
        """Adds a node's constraints. Returns its y and the x's in its subtree, keyed (course, path)."""
        y = self.var("y")
        if parent_y is not None:
            self.prob += y <= parent_y
        used: dict = {}
        kind = node_kind(node)

        if kind in ("all_of", "choose"):
            children = node["all_of"] if kind == "all_of" else node["from"]
            key = "all_of" if kind == "all_of" else "from"
            ys = []
            for i, child in enumerate(children):
                cy, cused = self.node(child, f"{path}/{key}/{i}", y)
                ys.append(cy)
                used.update(cused)
            if kind == "all_of":
                for cy in ys:
                    self.prob += cy >= y
            else:
                self.prob += pulp.lpSum(ys) >= node["choose"] * y
        elif kind == "specific_course":
            course = node["course"]
            if course in self.taken:
                x = self.var("x")
                self.prob += x == y
                self.slots[course].append(x)
                used[(course, path)] = x
                self.leaf_x[label(node, path)] = {course: x}
            else:
                self.prob += y == 0
        elif kind == "count":
            xs = {}
            for c in self.taken:
                if self.eligible(node["eligible_if"], c):
                    x = self.var("x")
                    self.prob += x <= y
                    self.slots[c].append(x)
                    xs[c] = x
                    used[(c, path)] = x
            self.thresholds(xs, node["thresholds"], y, path)
            self.leaf_x[label(node, path)] = xs
        # Placeholder families add no constraints: treated as met (audit reports them LOST).

        for i, check in enumerate(node.get("of_which", [])):
            cond = check.get("eligible_if")
            xs = {}
            for (c, p), x in used.items():
                if self.eligible(cond, c):
                    xs[f"{c}@{p}"] = x
            self.thresholds_over(xs, check["thresholds"], y, f"{path}/of_which/{i}")
        return y, used

    def thresholds_over(self, xs: dict[str, pulp.LpVariable], thresholds: list[dict], y, tag: str) -> None:
        by_course: dict[str, list] = {}
        for key, x in xs.items():
            by_course.setdefault(key.split("@")[0], []).append(x)
        for t in thresholds:
            if t["count_by"] == "courses":
                total = pulp.lpSum(xs.values())
            elif t["count_by"] == "units":
                total = pulp.lpSum(self.taken[c] * x for c, x_list in by_course.items() for x in x_list)
            else:
                total = self.weighted({c: pulp.lpSum(x_list) for c, x_list in by_course.items()},
                                      t["count_by"], tag)
            if t["op"] in ("min", "eq"):
                self.prob += total >= t["value"] * y
            if t["op"] in ("max", "eq"):
                self.prob += total <= t["value"]

    def build(self, root: dict) -> None:
        y, _ = self.node(root, "root")
        self.prob += y == 1
        for xs in self.slots.values():
            if len(xs) > 1:
                self.prob += pulp.lpSum(xs) <= 1  # one-slot rule
        # Objective: use as few courses as possible, so the assignment shown is the tightest one.
        self.prob += pulp.lpSum(x for xs in self.slots.values() for x in xs)

    def feasible(self) -> bool:
        self.prob.solve(pulp.PULP_CBC_CMD(msg=False))
        return pulp.LpStatus[self.prob.status] == "Optimal"


def _solve_once(root: dict, taken: dict[str, float], unknown_as: bool) -> _Builder | None:
    b = _Builder(taken, unknown_as)
    b.build(root)
    return b if b.feasible() else None


def solve(program: dict, taken: dict[str, float]) -> Verdict:
    """`taken` maps each course the student has taken to its units."""
    strict = _solve_once(program["root"], taken, unknown_as=False)
    lenient = strict or _solve_once(program["root"], taken, unknown_as=True)
    result = "pass" if strict else ("unknown" if lenient else "fail")

    assignment = {}
    if lenient:
        for leaf, xs in lenient.leaf_x.items():
            courses = sorted(c for c, x in xs.items() if (x.value() or 0) > 0.5)
            if courses:
                assignment[leaf] = courses

    unmet = []
    if result != "pass":
        for i, child in enumerate(program["root"].get("all_of", [])):
            if _solve_once(child, taken, unknown_as=True) is None:
                unmet.append(child.get("id", f"root/all_of/{i}"))
    return Verdict(result, assignment, unmet)
