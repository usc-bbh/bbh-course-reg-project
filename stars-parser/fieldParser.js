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
  const degreeMatch = text.match(
    /BACHELOR OF (\w+)\s*[-–]?\s*(BUSINESS ADMINISTRATION(?:\s*\([^)]+\))?|[A-Z][A-Z &]+)/i
  );

  let degree = "BS";
  let major = "";

  if (degreeMatch) {
    degree = `B${degreeMatch[1].charAt(0)}`;
    major = degreeMatch[2].trim();
  }

  const concMatch = major.match(/\(([^)]+)\)/);
  const concentration = concMatch ? concMatch[1].trim() : null;
  const baseMajor = major.replace(/\([^)]+\)/, "").trim();

  return { degree, major: baseMajor, concentration };
}

function extractProgramCode(text) {
  const match = text.match(/PROGRAM:\s*(\d+)/i);
  return match ? match[1] : null;
}

function extractCurrentPost(text) {
  const match = text.match(
    /CURRENT POST:.*?(\d{3,4})\s+(BS|BA|BFA|BM|BME)\s+(\w+)\s+(\w+)\s+(\d{5})/is
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
  const match = text.match(/CATALOG YEAR:\s*(\d{4,5})/i);
  if (!match) return null;
  const raw = match[1];
  return raw.length === 5
    ? `${raw.slice(0, 4)}-${raw.slice(0, 3)}${raw.slice(4)}`
    : raw;
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
  const earnedMatch = text.match(/EARNED:\s*([\d.]+)\s*GPA/i);
  const gpa = earnedMatch ? safeFloat(earnedMatch[1]) : null;

  const udMatch = text.match(
    /UPPER DIVISION COURSE\s+WORK APPLIED TO YOUR MAJOR:\s+EARNED:\s*([\d.]+)\s*GPA/i
  );
  const upperDivisionGpa = udMatch ? safeFloat(udMatch[1]) : null;

  return { gpa, upperDivisionGpa };
}

function extractCourses(text) {
  const completed = [];
  const inProgress = [];

  const courseRegex =
    /(\d{5})\s+([A-Z]{2,4}\s*\d{3}[A-Z]?)\s+(?:[A-Z\-x>]{0,6}\s+)?([\d.]+)\s+([A-Z][A-Z+\-]*|CR|P|W|UW|IP|NP|RG)?\s*(>IP)?\s+([A-Za-z][^\n]{3,50})/g;

  let match;
  while ((match = courseRegex.exec(text)) !== null) {
    const term = match[1];
    const code = match[2].replace(/\s+/, " ").trim();
    const units = safeFloat(match[3]);
    const grade = match[4] ? match[4].trim() : null;
    const isIP = !!match[5];
    const title = cleanTitle(match[6]);

    if (!term || !code || !title) continue;

    if (isIP || grade === "RG") {
      inProgress.push({ term, code, title, units });
    } else if (grade && grade !== "IP") {
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
  return val.toLowerCase() === "no minor declared" ? null : val;
}

function extractFlags(text) {
  const isTransfer = /TRNSFR WORK\s+(?:6[0-9]|[7-9]\d|1\d{2})\.0\s+TR/i.test(text);
  const studiedAbroad = /USC\s+3000|Off-Campus Studies|OVERSEAS STUDIES/i.test(text);
  const isStudentAthlete = /Student Athlete:/i.test(text);
  return { isTransfer, studiedAbroad, isStudentAthlete };
}

function extractRequirements(text) {
  const requirements = [];
  const checks = [
    { label: "128-Unit Minimum", pattern: /128 UNITS.*?(SATISFIED|NOT BEEN SATISFIED)/is },
    { label: "64-Unit Residency", pattern: /64-UNIT RESIDENCY.*?(SATISFIED|NOT BEEN SATISFIED)/is },
    { label: "32-Unit Upper Division", pattern: /32-UNIT UPPER DIVISION.*?(SATISFIED|NOT BEEN SATISFIED)/is },
    { label: "Cumulative GPA 2.0+", pattern: /2\.0 CUMULATIVE GPA.*?(SATISFIED|NOT BEEN SATISFIED)/is },
    { label: "Composition/Writing", pattern: /COMPOSITION\/WRITING.*?(SATISFIED|NOT BEEN SATISFIED)/is },
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
