#!/usr/bin/env python3
"""
Check that every JSON example in the taxonomy is valid and usable by code.

The model copies the examples it sees, so one bad example in
constraint_taxonomy.md leaks into every output. Run this after any edit to the
taxonomy. For each ```json block it checks:

  1. the block parses as JSON
  2. it validates against requirement_schema.json. The kind of block is told
     from its shape, so the taxonomy needs no extra markup:
       has "root"                  -> a whole program
       has "reason"                -> an unclassified entry
       has "family"/"all_of"/"choose" -> a node
       has "thresholds", no family -> an of_which check
  3. no old-format vocabulary remains (filter, pool, pool_rule, bound, measure,
     scope, fixed, source_text, the old family names, "..." placeholders)
  4. every "op": "eq" has "exactly" in the catalogue quote above it
  5. every eligible_if can be evaluated by eligibility.is_eligible

Usage
    python check_taxonomy.py                       # constraint_taxonomy.md
    python check_taxonomy.py --taxonomy draft.md   # another file
    python check_taxonomy.py --dir examples        # whole-program .json files
    python check_taxonomy.py --verbose             # every error, not the first 3

Exits non-zero if any block fails. Warnings are printed but don't fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft7Validator
from jsonschema.exceptions import best_match

from eligibility import UNKNOWN, is_eligible

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "requirement_schema.json"
TAXONOMY_PATH = HERE / "constraint_taxonomy.md"

# Keys from the old format. Outside a placeholder leaf's `details` any of these
# is an error. Inside `details` (course_reuse, sequencing, manual_review keep
# their old details until Phase 2) only the first group is an error; the rest
# are warnings, because FEEDBACK_phase1.md 2.3 says not to polish those yet.
OLD_KEYS_ALWAYS = {"filter", "pool", "pool_rule", "source_text"}
OLD_KEYS_OUTSIDE_DETAILS = {"bound", "measure", "scope", "fixed", "count", "constraints"}
OLD_FAMILIES = {"Course Selection", "Distribution Bounds", "Course Reuse", "Sequencing", "Manual Review"}

# Courses every eligible_if is tried against, on top of the ones it names.
SAMPLE_COURSES = ["CSCI 353", "CSCI 103L", "MATH 125", "ECON 401", "HIST 150"]


@dataclass
class Result:
    label: str
    kind: str = "?"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validators(schema: dict) -> dict[str, Draft7Validator]:
    """One validator per kind of block, each sharing the schema's definitions."""
    defs = schema["definitions"]

    def part(sub: dict) -> Draft7Validator:
        return Draft7Validator({"definitions": defs, **sub})

    return {
        "program": Draft7Validator(schema),
        "node": part({"$ref": "#/definitions/node"}),
        "check": part({"$ref": "#/definitions/check"}),
        "unclassified": part(schema["properties"]["unclassified"]["items"]),
    }


def classify(obj) -> str | None:
    if not isinstance(obj, dict):
        return None
    if "root" in obj:
        return "program"
    if "reason" in obj:
        return "unclassified"
    if "family" in obj or "all_of" in obj or "choose" in obj:
        return "node"
    if "thresholds" in obj:
        return "check"
    return None


def walk(obj, path=(), in_details=False):
    """Yields (path, key, value, in_details) for every key in every object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v, in_details
            yield from walk(v, path + (k,), in_details or k == "details")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (i,), in_details)


def where(path) -> str:
    return "/".join(str(p) for p in path) or "(top)"


def pick_branch(err, defs: dict) -> int | None:
    """For a oneOf (a node, or an eligible_if condition), the branch the object
    was evidently meant to be: the leaf whose `family` it names, or the group or
    condition whose key it uses. None if it matches no branch's shape."""
    inst = err.instance
    if not isinstance(inst, dict):
        return None
    for i, branch in enumerate(err.validator_value):
        if "$ref" in branch:
            branch = defs[branch["$ref"].split("/")[-1]]
        props = branch.get("properties", {})
        family = props.get("family", {}).get("const")
        if family is not None:
            if inst.get("family") == family:
                return i
            continue
        required = branch.get("required", [])
        if required and all(r in inst for r in required):
            return i
        if not required and inst and set(inst) <= set(props):
            return i
    return None


def schema_messages(err, defs: dict) -> list[str]:
    """A node can be any of several shapes, so jsonschema's own message is
    "... is not valid under any of the given schemas", which hides the cause.
    Follow the branch the object was meant to be and report its errors."""
    if err.validator in ("oneOf", "anyOf") and err.context:
        i = pick_branch(err, defs)
        if i is None:
            inst = err.instance
            if isinstance(inst, dict) and inst.get("family") in OLD_FAMILIES:
                hint = f"old family name '{inst['family']}' (see FEEDBACK_phase1.md section 6)"
            elif isinstance(inst, dict) and "family" in inst:
                hint = f"'{inst['family']}' is not a leaf family"
            elif isinstance(inst, dict):
                hint = f"keys {sorted(inst)} match no allowed shape"
            else:
                hint = f"{type(inst).__name__} where an object is expected"
            return [f"{where(err.absolute_path)}: {hint}"]
        out = []
        for sub in err.context:
            if sub.relative_schema_path[0] == i:
                out += schema_messages(sub, defs)
        return out or [f"{where(err.absolute_path)}: {err.message[:160]}"]
    if err.context:
        sub = best_match(err.context)
        return [f"{where(sub.absolute_path)}: {sub.message[:160]}"]
    return [f"{where(err.absolute_path)}: {err.message[:160]}"]


def lint(obj, quote: str | None, res: Result) -> None:
    for path, key, value, in_details in walk(obj):
        at = where(path + (key,))
        if key in OLD_KEYS_ALWAYS:
            res.errors.append(f"{at}: old key '{key}' (see FEEDBACK_phase1.md T1/T7/T9)")
        elif key in OLD_KEYS_OUTSIDE_DETAILS:
            (res.warnings if in_details else res.errors).append(f"{at}: old key '{key}'")
        if key == "..." or value == "...":
            res.errors.append(f"{at}: '...' placeholder. The model copies examples, so write them out in full")
        if key == "op" and value == "eq" and quote is not None and "exactly" not in quote.lower():
            res.errors.append(f"{at}: \"op\": \"eq\" but the quote doesn't say 'exactly'. Use \"min\" (T5)")


def check_evaluable(obj, res: Result) -> None:
    for path, key, value, _ in walk(obj):
        if key != "eligible_if":
            continue
        named = re.findall(r"[A-Z]{2,5} [0-9]{3}[A-Za-z]{0,3}", json.dumps(value))
        for course in SAMPLE_COURSES + named[:5]:
            try:
                answer = is_eligible(value, course)
            except Exception as exc:  # noqa: BLE001
                res.errors.append(f"{where(path + (key,))}: is_eligible can't evaluate it ({exc})")
                break
            if answer not in (True, False, UNKNOWN):
                res.errors.append(f"{where(path + (key,))}: is_eligible returned {answer!r}")
                break


def check_object(obj, vals: dict[str, Draft7Validator], label: str,
                 quote: str | None = None, expect: str | None = None) -> Result:
    """Runs every check on one parsed example. Reusable from check_results.py."""
    kind = classify(obj)
    res = Result(label, kind or "?")
    if kind is None:
        res.errors.append("unrecognised block: expected a node, an of_which check, "
                          "an unclassified entry or a whole program")
        return res
    if expect and kind != expect:
        res.errors.append(f"expected a {expect}, found a {kind}")
    defs = vals[kind].schema["definitions"]
    for err in sorted(vals[kind].iter_errors(obj), key=lambda e: [str(p) for p in e.path]):
        res.errors += schema_messages(err, defs)
    lint(obj, quote, res)
    check_evaluable(obj, res)
    return res


@dataclass
class Block:
    line: int  # line of the opening fence
    quote: str | None
    text: str


def extract_blocks(md: str) -> list[Block]:
    """Every ```json block, with the > quote just above it (blank lines allowed between)."""
    lines = md.split("\n")
    blocks, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith("```json"):
            start = i
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            k = start - 1
            while k >= 0 and not lines[k].strip():
                k -= 1
            quote_lines = []
            while k >= 0 and lines[k].lstrip().startswith(">"):
                quote_lines.insert(0, lines[k].lstrip()[1:].strip())
                k -= 1
            quote = " ".join(quote_lines) if quote_lines else None
            blocks.append(Block(start + 1, quote, "\n".join(lines[start + 1 : j])))
            i = j + 1
        else:
            i += 1
    return blocks


def check_taxonomy(path: Path, vals: dict[str, Draft7Validator]) -> list[Result]:
    results = []
    for b in extract_blocks(path.read_text(encoding="utf-8")):
        label = f"{path.name}:{b.line}"
        try:
            obj = json.loads(b.text)
        except json.JSONDecodeError as exc:
            results.append(Result(label, "?", [f"not valid JSON ({exc})"]))
            continue
        items = obj if isinstance(obj, list) else [obj]
        for n, item in enumerate(items):
            sub = label if len(items) == 1 else f"{label}[{n}]"
            results.append(check_object(item, vals, sub, b.quote))
    return results


def check_dir(path: Path, vals: dict[str, Draft7Validator]) -> list[Result]:
    results = []
    for f in sorted(path.glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            results.append(Result(f.name, "program", [f"not valid JSON ({exc})"]))
            continue
        results.append(check_object(obj, vals, f.name, expect="program"))
    return results


def report(results: list[Result], verbose: bool) -> int:
    failed = [r for r in results if r.errors]
    for r in results:
        status = "FAIL" if r.errors else "ok  "
        print(f"{status} {r.label:<32} {r.kind}")
        shown = r.errors if verbose else r.errors[:3]
        for e in shown:
            print(f"       - {e}")
        if len(r.errors) > len(shown):
            print(f"       ... and {len(r.errors) - len(shown)} more (use --verbose)")
        for w in (r.warnings if verbose else r.warnings[:1]):
            print(f"       warning: {w}")
    print(f"\n{len(results) - len(failed)} of {len(results)} pass, {len(failed)} fail.")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--taxonomy", default=str(TAXONOMY_PATH), help="markdown file to check")
    ap.add_argument("--dir", help="check whole-program .json files in this folder instead")
    ap.add_argument("--verbose", action="store_true", help="print every error and warning")
    args = ap.parse_args()

    vals = validators(load_schema())
    if args.dir:
        results = check_dir(Path(args.dir), vals)
    else:
        results = check_taxonomy(Path(args.taxonomy), vals)
    if not results:
        print("No JSON found to check.", file=sys.stderr)
        return 1
    return report(results, args.verbose)


if __name__ == "__main__":
    raise SystemExit(main())
