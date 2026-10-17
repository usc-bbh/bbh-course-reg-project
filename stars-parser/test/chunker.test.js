// Tests for docs/parser-brief.md §8's chunking pass.
//
// Run with:  node --test stars-parser/test/*.test.js
//
// Imports the real chunkReport/chunksByLabel, not a copy (§12).

import test from "node:test";
import assert from "node:assert";

import { chunkReport, chunksByLabel, StarsParseError } from "../chunker.js";

const DIV = "_".repeat(20);

test("throws when there's no PREPARED:/PROGRAM: anchor", () => {
  assert.throws(() => chunkReport("just some unrelated text"), StarsParseError);
});

test("throws when nothing is left after the anchor and page furniture are stripped", () => {
  // Only a PREPARED: line, which is itself stripped as page furniture —
  // nothing remains to split into blocks.
  assert.throws(() => chunkReport("PREPARED: 01/01/26"), StarsParseError);
});

test("labels a block by the words inside it, not its position", () => {
  const text = [
    "PREPARED: 01/01/26",
    DIV,
    "some header text",
    DIV,
    "A MINIMUM OF 128 UNITS IS REQUIRED",
    "20223 FOO101 4.0 A Some Course",
    DIV,
    "OTHER COURSES IN YOUR ACADEMIC ACCOUNT",
    "20223 BAR102 4.0 A Another Course",
    DIV,
    "NCAA SUPPLEMENTAL SECTION",
    "20223 FOO101 4.0 A Some Course",
  ].join("\n");

  const chunks = chunkReport(text);
  const labels = chunks.map((c) => c.label);

  assert.deepStrictEqual(labels, ["other", "masterCourseList", "otherCourses", "ncaa"]);
});

test("a section that's absent for this student produces no chunk for that label, not an error", () => {
  // No "128 UNITS", "OTHER COURSES" or "NCAA" anywhere — e.g. a minimal
  // report body with just a header and a residency block.
  const text = ["PREPARED: 01/01/26", DIV, "64-UNIT RESIDENCY", DIV, "BACHELOR OF SCIENCE"].join("\n");

  const chunks = chunkReport(text);
  assert.strictEqual(chunksByLabel(chunks, "masterCourseList"), "");
  assert.strictEqual(chunksByLabel(chunks, "ncaa"), "");
});

test("ignores blank-only blocks between adjacent dividers", () => {
  const text = ["PREPARED: 01/01/26", DIV, DIV, "128 UNITS block", DIV].join("\n");
  const chunks = chunkReport(text);
  assert.strictEqual(chunks.length, 1);
});

test("strips recurring page furniture rather than letting it split or mislabel a block", () => {
  const text = [
    "PREPARED: 01/01/26",
    DIV,
    "A MINIMUM OF 128 UNITS IS REQUIRED",
    "PREPARED: 01/01/26",
    "Academic Records and Registrar",
    "PROGRAM: 1835 PAGE 2",
    "20223 FOO101 4.0 A Some Course",
    DIV,
  ].join("\n");

  const chunks = chunkReport(text);
  assert.strictEqual(chunks.length, 1);
  assert.strictEqual(chunks[0].label, "masterCourseList");
  assert.doesNotMatch(chunks[0].text, /Academic Records/);
});
