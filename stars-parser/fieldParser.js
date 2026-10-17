// Takes the rebuilt text of a STARS report (textExtract.js) and pulls out
// all the structured fields we need.

import { chunkReport, chunksByLabel, StarsParseError } from "./chunker.js";

export { StarsParseError };

function safeFloat(str) {
  const n = parseFloat(str);
  return isNaN(n) ? null : n;
}

function cleanTitle(str) {
  return str ? str.trim().replace(/\s+/g, " ") : "";
}

function extractDegreeAndMajor(text) {
  // Degree type
  const degreeTypeMatch = text.match(/BACHELOR OF (SCIENCE|ARTS|FINE ARTS|MUSIC)/i);
  const degreeMap = { SCIENCE: "BS", ARTS: "BA", "FINE ARTS": "BFA", MUSIC: "BM" };
  const degree = degreeTypeMatch
    ? degreeMap[degreeTypeMatch[1].toUpperCase()] || "BS"
    : "BS";

  // Major — stop at "(" (a same-line concentration, e.g. "BUSINESS
  // ADMINISTRATION (MARKETING)"), "Academic"/"PROGRAM" trailing on the same
  // line, or a line break, whichever comes first.
  const majorMatch = text.match(
    /BACHELOR OF (?:SCIENCE|ARTS|FINE ARTS|MUSIC)\s*[-–]?\s*\n?\s*(BUSINESS ADMINISTRATION|[A-Z][A-Z ,&]*?)\s*(?:\(|Academic|PROGRAM|\n|$)/i
  );
  const major = majorMatch ? majorMatch[1].trim() : "";

  // Concentration — in parens either on the same line as the major
  // ("BUSINESS ADMINISTRATION (MARKETING)") or on its own line right after
  // it ("(FINANCE)", "(ENTREPRENEURSHIP AND INNOVATION)").
  const concMatch = text.match(/BACHELOR OF[\s\S]{0,120}?\(([^)]{2,60})\)/i);
  const concentration = concMatch ? concMatch[1].trim() : null;

  return { degree, major, concentration };
}

// STARS has two PROGRAM lines: "PROGRAM: CDAR6.04" (system) and "PROGRAM: 1832" (student).
// We want the numeric one.
function extractProgramCode(text) {
  const match = text.match(/PROGRAM:\s*(\d{3,5})\s/i);
  return match ? match[1] : null;
}

function extractCurrentPost(text) {
  const match = text.match(
    /CURRENT POST:.*?(\d{3,4})\s+(BS|BA|BFA|BM|BME)\.?\s+(\w+)\s+(\w+)\s+(\d{5})/is
  );
  if (match) {
    return {
      programCode: match[1],
      degreeType: match[2],
      majorCode: match[3],
      school: match[4],
      effectiveTerm: match[5],
    };
  }
  return {};
}

function extractCatalogYear(text) {
  const match = text.match(/CATALOG YEAR:\s*(\d{5})/i);
  if (!match) return null;
  const raw = match[1]; // e.g. "20243"
  const year = parseInt(raw.slice(0, 4));
  // Last digit is term (1=spring, 2=summer, 3=fall) — catalog year spans year to year+1
  return `${year}-${String(year + 1).slice(2)}`;
}

function extractClassLevel(text) {
  const match = text.match(
    /Current Class Level\s+(Freshman|Sophomore|Junior|Senior)/i
  );
  return match ? match[1] : null;
}

function extractGraduation(text) {
  const match = text.match(
    /Expected Graduation Date\s*[-–]?\s*(\d{1,2}\s+\w+\s+\d{4})/i
  );
  return match ? match[1].trim() : null;
}

function extractGPA(text) {
  const m = text.match(/EARNED:\s*([\d.]+)\s*GPA/i);
  const gpa = m ? safeFloat(m[1]) : null;
  const udm = text.match(
    /UPPER DIVISION COURSE[\s\S]{0,40}?EARNED:\s*([\d.]+)\s*GPA/i
  );
  return { gpa, upperDivisionGpa: udm ? safeFloat(udm[1]) : null };
}

// Case one (§7): a transfer mapped to a specific USC equivalent shows up
// under that real course code, with TR in the grade column.
// Case two: generic transfer credit with no USC equivalent shows up as a
// placeholder like TR-PSYC, TR-COMP-1 — not a real course code, and must be
// passed through unchanged rather than dropped or reshaped (§7's warning
// about the two tempting mistakes).
function classifySource(code, grade) {
  if (/^TR-/i.test(code)) return "transfer_generic";
  if (grade === "TR") return "transfer_specific";
  return "usc";
}

// Scans only the master course list and "other courses in your academic
// account" chunks — never the NCAA section or a requirement block, both of
// which repeat rows that are already counted here (§9). courseText is the
// concatenation of those two chunks; see parseStarsFields.
function extractCourses(courseText) {
  const completed = [];
  const inProgress = [];
  const seen = new Set();

  // Grammar (docs/reference/01-reading-a-stars-report.md, "Reading a course
  // row"): TERM  COURSE  [suffixes]  UNITS  GRADE  [>flags]  TITLE
  //   20253 ENST360 4.0 A- Public Policy...            (completed)
  //   20263 ENST450 4.0 RG >IP Sustainability in Practice   (in progress)
  const lines = courseText.split("\n");

  for (const line of lines) {
    // Must start with a 5-digit term.
    const termMatch = line.match(/^\s*(\d{5})\s+/);
    if (!termMatch) continue;

    const term = termMatch[1];
    // The 99993 "TRNSFR WORK ... Total Transfer Units" line is a roll-up
    // total, not a course — parsing it as one double-counts the student's
    // whole transfer balance (§7, item 1). Its "code" ("TRNSFR WORK") also
    // won't match codeMatch below, but skip it explicitly so that stays
    // true even if the summary wording changes.
    if (term === "99993") continue;

    const rest = line.slice(termMatch[0].length);

    // Course code: 2-4 letters + optional space + 3 digits + optional
    // letter, or a generic transfer placeholder like TR-PSYC / TR-COMP-1.
    const codeMatch = rest.match(/^(TR-[A-Z0-9-]+|[A-Z]{2,4}\s*\d{3}[A-Z]?)\s+/i);
    if (!codeMatch) continue;

    const code = codeMatch[1].replace(/\s+/, " ").trim();
    const afterCode = rest.slice(codeMatch[0].length);

    // Units: a decimal number.
    const unitsMatch = afterCode.match(/([\d.]+)\s+/);
    if (!unitsMatch) continue;

    const units = safeFloat(unitsMatch[1]);
    const afterUnits = afterCode.slice(unitsMatch.index + unitsMatch[0].length);

    // Check for in-progress marker (>IP appears right before or in the title)
    const isIP = />IP/i.test(afterUnits);

    // Grade: letter grade, TR (transfer), or RG (in progress).
    const gradeMatch = afterUnits.match(/^([A-Z][A-Z+\-]*|CR|P|W|NP|RG)\s+/);
    const grade = gradeMatch ? gradeMatch[1].trim() : null;

    // Title: everything after grade, strip >IP prefix if present.
    const afterGrade = gradeMatch ? afterUnits.slice(gradeMatch[0].length) : afterUnits;
    const title = cleanTitle(afterGrade.replace(/^>IP[a-z]*/i, "").trim());

    if (!title || title.length < 3) continue;

    // Combine the master list with "other courses", then dedupe by
    // (term, course) — a course can legitimately appear in both, PE
    // commonly does (§9).
    const key = `${term}|${code}`;
    if (seen.has(key)) continue;
    seen.add(key);

    const source = classifySource(code, grade);

    if (isIP || grade === "RG") {
      inProgress.push({ term, code, title, units, grade, source });
    } else if (grade && !["IP", "RG"].includes(grade)) {
      completed.push({ term, code, title, units, grade, source });
    }
  }

  return { completed, inProgress };
}

function extractTransferUnits(text) {
  const match = text.match(/TRNSFR\s+WORK\s+([\d.]+)\s+TR/i);
  return match ? safeFloat(match[1]) : 0;
}

function extractMinor(text) {
  const match = text.match(/MINOR:\s*(.+?)(?:\s+\d{5}|\n)/i);
  if (!match) return null;
  const val = match[1].trim();
  return /no minor/i.test(val) ? null : val;
}

function extractFlags(text) {
  return {
    isTransfer: /TRNSFR WORK\s+(?:6[0-9]|[7-9]\d|1\d{2})\.0\s+TR/i.test(text),
    studiedAbroad: /USC\s+3000|Off-Campus Studies|OVERSEAS STUDIES/i.test(text),
    isStudentAthlete: /Student Athlete:/i.test(text),
  };
}

function extractRequirements(text) {
  const requirements = [];
  const checks = [
    { label: "128-Unit Minimum", pattern: /128 UNITS[\s\S]{0,80}?(SATISFIED|NOT BEEN SATISFIED)/i },
    { label: "64-Unit Residency", pattern: /64-UNIT RESIDENCY[\s\S]{0,80}?(SATISFIED|NOT BEEN SATISFIED)/i },
    { label: "32-Unit Upper Division", pattern: /32-UNIT UPPER DIVISION[\s\S]{0,80}?(SATISFIED|NOT BEEN SATISFIED)/i },
    { label: "Cumulative GPA 2.0+", pattern: /2\.0 CUMULATIVE GPA[\s\S]{0,80}?(SATISFIED|NOT BEEN SATISFIED)/i },
    { label: "Composition/Writing", pattern: /COMPOSITION\/WRITING[\s\S]{0,80}?(SATISFIED|NOT BEEN SATISFIED)/i },
  ];

  for (const { label, pattern } of checks) {
    const match = text.match(pattern);
    if (match) {
      requirements.push({
        label,
        status: /NOT BEEN SATISFIED/i.test(match[0]) ? "no" : "ok",
      });
    }
  }

  return requirements;
}

// The master course list's own "EARNED: X UNITS" line, used only as the
// self-check §10 recommends: the units implied by the parsed course list
// should reconcile with the report's own total. This is a best-effort
// sum — it doesn't yet account for excluded/deleted-credit flags (>D, >Z,
// >EX) or unit caps (PE, individual music instruction), so a mismatch is
// surfaced as a warning to look into, not proof the parse is wrong.
function extractEarnedUnits(masterCourseListText) {
  const match = masterCourseListText.match(/EARNED:\s*([\d.]+)\s*UNITS/i);
  return match ? safeFloat(match[1]) : null;
}

export function parseStarsFields(rawText) {
  // §8/§9: cut the report into labelled chunks first, so course rows are
  // only ever read from the master list and "other courses" — never from a
  // requirement block or the NCAA section, both of which repeat rows
  // already counted here.
  const chunks = chunkReport(rawText);
  const masterCourseListText = chunksByLabel(chunks, "masterCourseList");
  const otherCoursesText = chunksByLabel(chunks, "otherCourses");

  // §10: fail loudly. A parser that throws naming what's missing is safer
  // than one that quietly returns a plausible-looking partial object — the
  // validator can't tell an empty completedCourses caused by a missed
  // landmark from a student who has genuinely taken nothing.
  if (!masterCourseListText) {
    throw new StarsParseError(
      "No master course list found (expected a block containing '128 UNITS') — refusing to guess at completedCourses/inProgressCourses."
    );
  }

  const { degree, major, concentration } = extractDegreeAndMajor(rawText);
  if (!major) {
    throw new StarsParseError(
      "Couldn't find the major — no 'BACHELOR OF ...' line in the report header."
    );
  }

  const classLevel = extractClassLevel(rawText);
  if (!classLevel) {
    throw new StarsParseError(
      "Couldn't find class level — no 'Current Class Level' line in the report."
    );
  }

  const { gpa, upperDivisionGpa } = extractGPA(rawText);
  if (gpa == null) {
    throw new StarsParseError(
      "Couldn't find cumulative GPA — no 'EARNED: ... GPA' line in the report."
    );
  }

  const currentPost = extractCurrentPost(rawText);
  const { completed, inProgress } = extractCourses(
    [masterCourseListText, otherCoursesText].join("\n")
  );
  const { isTransfer, studiedAbroad, isStudentAthlete } = extractFlags(rawText);

  const warnings = [];
  const earnedUnits = extractEarnedUnits(masterCourseListText);
  if (earnedUnits != null) {
    const completedUnits = completed.reduce((sum, c) => sum + (c.units || 0), 0);
    if (Math.abs(completedUnits - earnedUnits) > 0.01) {
      warnings.push(
        `Parsed completed-course units (${completedUnits}) don't reconcile with the report's own EARNED total (${earnedUnits}) — see §10.`
      );
    }
  }

  return {
    degree,
    major,
    concentration: concentration || null,
    majorCode: currentPost.majorCode || null,
    programCode: extractProgramCode(rawText) || currentPost.programCode || null,
    catalogYear: extractCatalogYear(rawText),
    classLevel,
    expectedGraduation: extractGraduation(rawText),
    gpa,
    upperDivisionGpa,
    completedCourses: completed,
    inProgressCourses: inProgress,
    transferUnits: extractTransferUnits(rawText),
    minor: extractMinor(rawText),
    isTransfer,
    studiedAbroad,
    isStudentAthlete,
    requirements: extractRequirements(rawText),
    warnings,
  };
}
