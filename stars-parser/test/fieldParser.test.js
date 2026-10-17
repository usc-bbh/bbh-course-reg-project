// End-to-end test of parseStarsFields against a hand-built single-column
// sample (test/fixtures/sample-single-column.txt), reflowed from a real
// redacted parser fixture into the single-column layout parser-brief.md
// now targets, with a transfer_specific row, a transfer_generic row, and an
// NCAA section added to exercise §7 and §9.
//
// Not yet checked against a real experience.usc.edu export (see README).
//
// Run with:  node --test stars-parser/test/*.test.js
//
// Imports the real parseStarsFields, not a copy (§12).

import test from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { parseStarsFields, StarsParseError } from "../fieldParser.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const sample = fs.readFileSync(
  path.join(__dirname, "fixtures", "sample-single-column.txt"),
  "utf-8"
);

test("parses the five required fields (parser-brief §6)", () => {
  const r = parseStarsFields(sample);

  assert.strictEqual(r.major, "BUSINESS ADMINISTRATION");
  assert.strictEqual(r.concentration, "MARKETING");
  assert.strictEqual(r.classLevel, "Senior");
  assert.strictEqual(r.gpa, 3.429);
  assert.ok(Array.isArray(r.completedCourses));
  assert.ok(Array.isArray(r.inProgressCourses));
});

test("only reads course rows from the master list and other-courses chunks (§9)", () => {
  const r = parseStarsFields(sample);

  const codes = r.completedCourses.map((c) => c.code).sort();
  assert.deepStrictEqual(codes, ["BUAD302", "BUAD304", "ESRM150", "PHED165", "TR-COMP-1", "TR-PSYC"]);

  // BUAD304/BUAD302 also appear in the upper-division-major-GPA block and
  // in the NCAA section. Neither may inflate the count.
  assert.strictEqual(r.completedCourses.filter((c) => c.code === "BUAD304").length, 1);
  assert.strictEqual(r.completedCourses.filter((c) => c.code === "BUAD302").length, 1);

  // WRIT150 only appears inside the writing-requirement block — never in
  // the master list or other-courses — so it must not show up at all.
  assert.ok(!codes.includes("WRIT150"));
});

test("skips the 99993 aggregate transfer line rather than counting it as a course", () => {
  const r = parseStarsFields(sample);
  assert.ok(!r.completedCourses.some((c) => c.term === "99993"));
});

test("tags course source per §7: usc / transfer_specific / transfer_generic", () => {
  const r = parseStarsFields(sample);
  const byCode = Object.fromEntries(r.completedCourses.map((c) => [c.code, c]));

  assert.strictEqual(byCode.BUAD304.source, "usc");
  assert.strictEqual(byCode.ESRM150.source, "transfer_specific");
  assert.strictEqual(byCode.ESRM150.grade, "TR");
  assert.strictEqual(byCode["TR-PSYC"].source, "transfer_generic");
  assert.strictEqual(byCode["TR-COMP-1"].source, "transfer_generic");

  // Generic placeholders are passed through unchanged, not cleaned up into
  // something that looks like a real course code (§7's second trap).
  assert.strictEqual(byCode["TR-PSYC"].code, "TR-PSYC");
});

test("an in-progress row (RG / >IP) is not counted as completed", () => {
  const r = parseStarsFields(sample);

  assert.strictEqual(r.inProgressCourses.length, 1);
  assert.strictEqual(r.inProgressCourses[0].code, "BUAD425");
  assert.strictEqual(r.inProgressCourses[0].grade, "RG");
  assert.strictEqual(r.inProgressCourses[0].source, "usc");
  assert.ok(!r.completedCourses.some((c) => c.code === "BUAD425"));
});

test("every course carries term/code/grade/units/source (§6)", () => {
  const r = parseStarsFields(sample);
  for (const course of [...r.completedCourses, ...r.inProgressCourses]) {
    assert.strictEqual(typeof course.term, "string");
    assert.strictEqual(typeof course.code, "string");
    assert.strictEqual(typeof course.grade, "string");
    assert.strictEqual(typeof course.units, "number");
    assert.ok(["usc", "transfer_specific", "transfer_generic"].includes(course.source));
  }
});

test("the reconciliation self-check is quiet when the numbers agree", () => {
  const r = parseStarsFields(sample);
  assert.deepStrictEqual(r.warnings, []);
});

test("the reconciliation self-check warns, but doesn't throw, on a mismatch", () => {
  const mismatched = sample.replace("EARNED: 19.00 UNITS", "EARNED: 999.00 UNITS");
  const r = parseStarsFields(mismatched);
  assert.strictEqual(r.warnings.length, 1);
  assert.match(r.warnings[0], /don't reconcile/);
});

test("throws naming what's missing rather than returning a partial object (§10)", () => {
  const noMajor = sample.replace("BACHELOR OF SCIENCE", "");
  assert.throws(() => parseStarsFields(noMajor), StarsParseError);

  // Both EARNED:...GPA lines have to go — otherwise the (unrelated)
  // upper-division-major GPA further down becomes the new first match.
  const noGpa = sample.replace("EARNED: 3.429 GPA", "").replace("EARNED: 3.372 GPA", "");
  assert.throws(() => parseStarsFields(noGpa), StarsParseError);

  const noMasterList = sample.replace(
    "IP A MINIMUM OF 128 UNITS IS REQUIRED FOR DEGREE COMPLETION:",
    ""
  );
  assert.throws(() => parseStarsFields(noMasterList), StarsParseError);
});
