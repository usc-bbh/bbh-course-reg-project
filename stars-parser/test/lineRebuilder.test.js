// Tests for rebuilding PDF text fragments into lines.
//
// Run with:  node --test stars-parser/test/*.test.js
//
// These import the real rebuildLines and the real parseStarsFields rather
// than holding their own copies, so a regression in either module fails the
// suite. (docs/parser-brief.md §12 notes that parser.test.js does the
// opposite and therefore proves nothing.)
//
// No PDF and no browser involved: pdf.js hands us an array of fragments,
// each with a transform matrix, so a test can build that array directly.
// transform[4] is the x offset, transform[5] the baseline y.

import test from "node:test";
import assert from "node:assert";

import { rebuildLines } from "../lineRebuilder.js";
import { parseStarsFields, StarsParseError } from "../fieldParser.js";

// Helper: a pdf.js-shaped text fragment.
const frag = (str, x, y) => ({ str, transform: [1, 0, 0, 1, x, y] });

// What the old implementation did, kept here only for contrast.
const flattenAsBefore = (items) => items.map((i) => i.str).join(" ");

// A miniature STARS page, with fragments in the order pdf.js normally emits
// them (roughly reading order). Tokens are split mid-number the way they
// genuinely arrive — "20243" as "2024" + "3" — which is what made the old
// space-joining lossy.
const PAGE_FRAGMENTS = [
  frag("CATALOG YEAR: ", 40, 700),
  frag("2024", 150, 700),
  frag("3", 176, 700),

  frag("EARNED: ", 40, 600),
  frag("3.", 112, 600),
  frag("42", 128, 600),
  frag(" GPA", 150, 600),

  frag("20", 40, 500),
  frag("243", 60, 500),
  frag(" BUAD304 -O 4.0 B- Organizational Behavior", 96, 500),

  frag("Current Class Level", 40, 400),
  frag("   Junior", 180, 400),
];

const EXPECTED_LINES = [
  "CATALOG YEAR: 20243",
  "EARNED: 3.42 GPA",
  "20243 BUAD304 -O 4.0 B- Organizational Behavior",
  "Current Class Level   Junior",
];

test("groups fragments into the visual lines of the page", () => {
  assert.deepStrictEqual(rebuildLines(PAGE_FRAGMENTS).split("\n"), EXPECTED_LINES);
});

test("orders lines top-down and fragments left-to-right regardless of input order", () => {
  // Same fragments, deliberately scrambled. Position must decide the output,
  // not the order pdf.js happened to hand them over in.
  const scrambled = [...PAGE_FRAGMENTS].reverse();
  assert.deepStrictEqual(rebuildLines(scrambled).split("\n"), EXPECTED_LINES);

  const shuffled = [4, 0, 9, 2, 11, 6, 1, 8, 3, 10, 5, 7].map((i) => PAGE_FRAGMENTS[i]);
  assert.deepStrictEqual(rebuildLines(shuffled).split("\n"), EXPECTED_LINES);
});

test("joins fragments within a line without inserting spaces into tokens", () => {
  const text = rebuildLines(PAGE_FRAGMENTS);

  assert.match(text, /CATALOG YEAR: 20243/);
  assert.match(text, /EARNED: 3\.42 GPA/);

  // The old bug: " " between fragments split numbers apart.
  assert.doesNotMatch(text, /2024 3|3\. 42/);
});

test("produces one line per visual row, not one line per page", () => {
  assert.strictEqual(rebuildLines(PAGE_FRAGMENTS).split("\n").length, 4);
  assert.strictEqual(flattenAsBefore(PAGE_FRAGMENTS).split("\n").length, 1);
});

// A miniature but complete report: same page as above, plus the landmarks
// parseStarsFields now requires before it will trust anything (§10) — a
// PREPARED:/PROGRAM: anchor, a "BACHELOR OF ..." line for major, and a
// "128 UNITS" line so chunkReport labels this block as the master course
// list. Kept separate from PAGE_FRAGMENTS so the geometry-only tests above
// don't have to know about parser-level landmarks.
const FULL_REPORT_FRAGMENTS = [
  frag("PREPARED: 02/10/26", 40, 900),
  frag("BACHELOR OF SCIENCE - MARKETING PROGRAM", 40, 850),
  frag("A MINIMUM OF 128 UNITS IS REQUIRED FOR DEGREE COMPLETION", 40, 800),
  ...PAGE_FRAGMENTS,
];

test("fields the old extraction lost are recovered downstream", () => {
  const rebuilt = parseStarsFields(rebuildLines(FULL_REPORT_FRAGMENTS));

  // GPA — the bug Agastya reported. "3." + "42" became "3. 42".
  assert.strictEqual(rebuilt.gpa, 3.42);

  // Catalog year — broken by intra-token spaces, not by line structure:
  // \d{5} cannot match "2024 3".
  assert.strictEqual(rebuilt.catalogYear, "2024-25");

  assert.strictEqual(rebuilt.classLevel, "Junior");

  // Course rows — the row pattern is anchored at a line start, so with the
  // whole page collapsed onto one line the old path found none at all.
  assert.strictEqual(rebuilt.completedCourses.length, 1);

  assert.deepStrictEqual(rebuilt.completedCourses[0], {
    term: "20243",
    code: "BUAD304",
    title: "Organizational Behavior",
    units: 4,
    grade: "B-",
    source: "usc",
  });

  // Flattening still breaks GPA the same way (intra-token space defeats
  // \d+\.\d+), but parseStarsFields no longer returns that silently as
  // `gpa: null` alongside an otherwise plausible-looking object (§10's
  // "returns nothing is safer than a plausible-looking subset") — it
  // throws, naming what's missing.
  assert.throws(
    () => parseStarsFields(flattenAsBefore(FULL_REPORT_FRAGMENTS)),
    StarsParseError
  );
});

test("handles an empty page without throwing", () => {
  assert.strictEqual(rebuildLines([]), "");
});
