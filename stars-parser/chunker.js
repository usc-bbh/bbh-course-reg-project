// Cuts a rebuilt STARS report into labelled chunks so course extraction only
// ever scans the parts of the report that are actually the master course
// list, never a requirement block or the NCAA section repeating the same
// rows. See docs/parser-brief.md §8 and §9.
//
// Only the course-scanning path uses this. major/classLevel/gpa/catalogYear/
// programCode/minor keep matching against the full rebuilt text in
// fieldParser.js, same as before — they're each anchored by a label that
// only occurs once in a real report (e.g. "CURRENT POST:"), so chunking
// buys them nothing and isn't worth the risk of a wrong chunk boundary
// hiding the one place the field lives.
//
// Not yet checked against a real single-column export — no PDF exists in
// this repo. Built from the report structure in
// docs/reference/01-reading-a-stars-report.md and the literal anchor phrases
// docs/parser-brief.md §8 calls out, and tested against a hand-built sample
// (test/fixtures/sample-single-column.txt) reflowed from the redacted OCR
// fixture into single-column order. If a real report doesn't chunk the way
// this expects, the report wins — see CONTRIBUTING / the brief's own note
// to that effect.

export class StarsParseError extends Error {
  constructor(message) {
    super(message);
    this.name = "StarsParseError";
  }
}

// Everything before the first PREPARED: or PROGRAM: line is print preamble
// (student name/ID) and holds nothing the parser needs (§8 step one).
const BODY_START = /^(PREPARED|PROGRAM):.*$/m;

// Section dividers: a line that is nothing but a run of 5+ underscores or
// asterisks (§8 step two, ~27 underscore dividers in a typical report).
const DIVIDER = /^[ \t]*[_*]{5,}[ \t]*$/;

// Recurring page furniture (reference doc, "Where the personal information
// sits"): the per-page timestamp/institution banner. Stripped for
// cleanliness before chunking; not load-bearing, since none of these lines
// start with a 5-digit term and so can't be mistaken for a course row.
const PAGE_FURNITURE = [
  /^PREPARED:/,
  /^University of Southern California\b/,
  /^Academic Records and Registrar$/,
  /^PROGRAM:\s*\S+\s+PAGE\s*\d+$/i,
];

function isPageFurniture(line) {
  const trimmed = line.trim();
  return PAGE_FURNITURE.some((re) => re.test(trimmed));
}

// Labels matched by the literal anchor words the brief and reference doc
// call out (§8 step three: "label each chunk by distinctive words inside
// it, not by its position"). First match wins. Anything that matches none
// of these — every requirement block (major, GE, writing, minor, residency,
// GPA) — stays "other" and is deliberately never scanned for course rows:
// that's what makes §9's "never collect courses from inside a requirement
// block" true by construction rather than by trying to detect requirement
// blocks specifically.
const LABEL_RULES = [
  // Checked first: the NCAA section re-lists coursework that already
  // appears in the master list or "other courses" (§9), and this order
  // makes sure that re-listing can never win a later, broader rule.
  { label: "ncaa", test: (t) => /\bNCAA\b/.test(t) },
  { label: "otherCourses", test: (t) => /OTHER COURSES/.test(t) },
  { label: "masterCourseList", test: (t) => /\b128\s*UNITS\b/.test(t) },
  { label: "header", test: (t) => /BACHELOR OF/.test(t) },
];

function labelOf(text) {
  for (const { label, test } of LABEL_RULES) {
    if (test(text)) return label;
  }
  return "other";
}

// Splits the report body into { label, text } chunks.
export function chunkReport(fullText) {
  const startMatch = fullText.match(BODY_START);
  if (!startMatch) {
    throw new StarsParseError(
      "No PREPARED: or PROGRAM: line found — this doesn't look like a STARS report export."
    );
  }

  const body = fullText.slice(startMatch.index);
  const lines = body.split("\n").filter((line) => !isPageFurniture(line));

  const blocks = [];
  let current = [];
  for (const line of lines) {
    if (DIVIDER.test(line)) {
      if (current.some((l) => l.trim())) blocks.push(current.join("\n"));
      current = [];
    } else {
      current.push(line);
    }
  }
  if (current.some((l) => l.trim())) blocks.push(current.join("\n"));

  if (blocks.length === 0) {
    throw new StarsParseError(
      "No section dividers found after the report body starts — line rebuilding or divider detection may be broken (expected dozens of underscore-divided blocks per §5/§8)."
    );
  }

  return blocks.map((text) => ({ label: labelOf(text), text }));
}

// All chunk text for a label, joined — "" if the section is absent (e.g. no
// minor, not an athlete). Absence is a normal case, never an error (§8:
// "always handle 'this section is absent' as a normal case rather than an
// error").
export function chunksByLabel(chunks, label) {
  return chunks
    .filter((c) => c.label === label)
    .map((c) => c.text)
    .join("\n");
}
