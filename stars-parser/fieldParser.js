// Takes raw text from either textExtract or ocrExtract and pulls out
// all the structured fields we need from a STARS report.

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

  // Major — stop before "Academic" or "PROGRAM" which appear on the same line after the title
  const majorMatch = text.match(
    /BACHELOR OF (?:SCIENCE|ARTS|FINE ARTS|MUSIC)\s*[-–]?\s*(BUSINESS ADMINISTRATION|[A-Z][A-Z ,&]+?)(?:\s+Academic|\s+PROGRAM|\s*\n)/i
  );
  const major = majorMatch ? majorMatch[1].trim() : "";

  // Concentration — often on the next line in parens: "(FINANCE)" or "(ENTREPRENEURSHIP AND INNOVATION)"
  const concMatch = text.match(/BACHELOR OF[\s\S]{0,120}?\n\s*\(([^)]{3,60})\)/i);
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

function extractCourses(text) {
  const completed = [];
  const inProgress = [];

  // Course line formats seen in STARS OCR output:
  //   TERM  CODE      FLAGS  UNITS  GRADE  TITLE
  //   20243 BUAD304   -O     4.0    B-     Organizational Behavior...
  //   20261 BUAD302   4.0    RG     >IPCommunication Strategy...   (in-progress, >IP joined to title)
  //   20261 USC 3000  12.0   RG     >IPOff-Campus Studies
  const lines = text.split("\n");

  for (const line of lines) {
    // Must start with a 5-digit term
    const termMatch = line.match(/^(\d{5})\s+/);
    if (!termMatch) continue;

    const term = termMatch[1];
    const rest = line.slice(termMatch[0].length);

    // Course code: 2-4 letters + optional space + 3 digits + optional letter
    const codeMatch = rest.match(/^([A-Z]{2,4}\s*\d{3}[A-Z]?)\s+/i);
    if (!codeMatch) continue;

    const code = codeMatch[1].replace(/\s+/, " ").trim();
    const afterCode = rest.slice(codeMatch[0].length);

    // Units: a decimal number
    const unitsMatch = afterCode.match(/([\d.]+)\s+/);
    if (!unitsMatch) continue;

    const units = safeFloat(unitsMatch[1]);
    const afterUnits = afterCode.slice(unitsMatch.index + unitsMatch[0].length);

    // Check for in-progress marker (>IP appears right before or in the title)
    const isIP = />IP/i.test(afterUnits);

    // Grade: letter grade or RG for in-progress
    const gradeMatch = afterUnits.match(/^([A-Z][A-Z+\-]*|CR|P|W|NP|RG)\s+/);
    const grade = gradeMatch ? gradeMatch[1].trim() : null;

    // Title: everything after grade, strip >IP prefix if present
    const afterGrade = gradeMatch ? afterUnits.slice(gradeMatch[0].length) : afterUnits;
    const title = cleanTitle(afterGrade.replace(/^>IP[a-z]*/i, "").trim());

    if (!title || title.length < 3) continue;

    if (isIP || grade === "RG") {
      inProgress.push({ term, code, title, units });
    } else if (grade && !["IP", "RG"].includes(grade)) {
      completed.push({ term, code, title, units, grade });
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

export function parseStarsFields(rawText) {
  const { degree, major, concentration } = extractDegreeAndMajor(rawText);
  const currentPost = extractCurrentPost(rawText);
  const { gpa, upperDivisionGpa } = extractGPA(rawText);
  const { completed, inProgress } = extractCourses(rawText);
  const { isTransfer, studiedAbroad, isStudentAthlete } = extractFlags(rawText);

  return {
    degree,
    major,
    concentration: concentration || null,
    majorCode: currentPost.majorCode || null,
    programCode: extractProgramCode(rawText) || currentPost.programCode || null,
    catalogYear: extractCatalogYear(rawText),
    classLevel: extractClassLevel(rawText),
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
  };
}
