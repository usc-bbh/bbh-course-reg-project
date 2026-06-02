import fs from 'fs';
import path from 'path';

function safeFloat(str) { const n = parseFloat(str); return isNaN(n) ? null : n; }
function cleanTitle(str) { return str ? str.trim().replace(/\s+/g, ' ') : ''; }

function extractDegreeAndMajor(text) {
  const degreeTypeMatch = text.match(/BACHELOR OF (SCIENCE|ARTS|FINE ARTS|MUSIC)/i);
  const degreeMap = { SCIENCE: 'BS', ARTS: 'BA', 'FINE ARTS': 'BFA', MUSIC: 'BM' };
  const degree = degreeTypeMatch ? (degreeMap[degreeTypeMatch[1].toUpperCase()] || 'BS') : 'BS';
  const majorMatch = text.match(/BACHELOR OF (?:SCIENCE|ARTS|FINE ARTS|MUSIC)\s*[-–]?\s*(BUSINESS ADMINISTRATION|[A-Z][A-Z ,&]+?)(?:\s+Academic|\s+PROGRAM|\s*\n)/i);
  const major = majorMatch ? majorMatch[1].trim() : '';
  const concMatch = text.match(/BACHELOR OF[\s\S]{0,120}?\n\s*\(([^)]{3,60})\)/i);
  const concentration = concMatch ? concMatch[1].trim() : null;
  return { degree, major, concentration };
}
function extractProgramCode(text) {
  const match = text.match(/PROGRAM:\s*(\d{3,5})\s/i);
  return match ? match[1] : null;
}
function extractCurrentPost(text) {
  const match = text.match(/CURRENT POST:.*?(\d{3,4})\s+(BS|BA|BFA|BM|BME)\.?\s+(\w+)\s+(\w+)\s+(\d{5})/is);
  if (match) return { programCode: match[1], degreeType: match[2], majorCode: match[3], school: match[4] };
  return {};
}
function extractCatalogYear(text) {
  const match = text.match(/CATALOG YEAR:\s*(\d{5})/i);
  if (!match) return null;
  const year = parseInt(match[1].slice(0, 4));
  return `${year}-${String(year + 1).slice(2)}`;
}
function extractClassLevel(text) {
  const match = text.match(/Current Class Level\s+(Freshman|Sophomore|Junior|Senior)/i);
  return match ? match[1] : null;
}
function extractGraduation(text) {
  const match = text.match(/Expected Graduation Date\s*[-–]?\s*(\d{1,2}\s+\w+\s+\d{4})/i);
  return match ? match[1].trim() : null;
}
function extractGPA(text) {
  const m = text.match(/EARNED:\s*([\d.]+)\s*GPA/i);
  return { gpa: m ? safeFloat(m[1]) : null };
}
function extractCourses(text) {
  const completed = [], inProgress = [];
  const lines = text.split('\n');
  for (const line of lines) {
    const termMatch = line.match(/^(\d{5})\s+/);
    if (!termMatch) continue;
    const term = termMatch[1];
    const rest = line.slice(termMatch[0].length);
    const codeMatch = rest.match(/^([A-Z]{2,4}\s*\d{3}[A-Z]?)\s+/i);
    if (!codeMatch) continue;
    const code = codeMatch[1].replace(/\s+/, ' ').trim();
    const afterCode = rest.slice(codeMatch[0].length);
    const unitsMatch = afterCode.match(/([\d.]+)\s+/);
    if (!unitsMatch) continue;
    const units = safeFloat(unitsMatch[1]);
    const afterUnits = afterCode.slice(unitsMatch.index + unitsMatch[0].length);
    const isIP = />IP/i.test(afterUnits);
    const gradeMatch = afterUnits.match(/^([A-Z][A-Z+\-]*|CR|P|W|NP|RG)\s+/);
    const grade = gradeMatch ? gradeMatch[1].trim() : null;
    const afterGrade = gradeMatch ? afterUnits.slice(gradeMatch[0].length) : afterUnits;
    const title = cleanTitle(afterGrade.replace(/^>IP[a-z]*/i, '').trim());
    if (!title || title.length < 3) continue;
    if (isIP || grade === 'RG') inProgress.push({ term, code, title, units });
    else if (grade && !['IP','RG'].includes(grade)) completed.push({ term, code, title, units, grade });
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
function parseStarsFields(rawText) {
  const { degree, major, concentration } = extractDegreeAndMajor(rawText);
  const currentPost = extractCurrentPost(rawText);
  const { gpa } = extractGPA(rawText);
  const { completed, inProgress } = extractCourses(rawText);
  const { isTransfer, studiedAbroad, isStudentAthlete } = extractFlags(rawText);
  return {
    degree, major, concentration: concentration || null,
    majorCode: currentPost.majorCode || null,
    programCode: extractProgramCode(rawText) || currentPost.programCode || null,
    catalogYear: extractCatalogYear(rawText),
    classLevel: extractClassLevel(rawText),
    expectedGraduation: extractGraduation(rawText),
    gpa, completedCourses: completed, inProgressCourses: inProgress,
    transferUnits: extractTransferUnits(rawText),
    minor: extractMinor(rawText),
    isTransfer, studiedAbroad, isStudentAthlete,
  };
}

const dir = '/tmp/stars_text';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.txt') && !f.startsWith('.')).sort();

// What we expect from our earlier manual analysis
const expected = {
  '1Transfer_StudyAbroad_BUAD.txt': { majorCode: 'BUAD', programCode: '486', classLevel: 'Senior', isTransfer: true, studiedAbroad: true, minor: null },
  '2X_X_BUAD.txt':                  { majorCode: 'BEI',  programCode: '1832', classLevel: 'Senior', isTransfer: false, studiedAbroad: false, minor: 'Designing Products' },
  '3X_StudyAbroad_BUAD.txt':        { majorCode: 'BFIN', programCode: '1833', classLevel: 'Senior', isTransfer: false, studiedAbroad: true, minor: 'Dance' },
  '4X_X_BUAD.txt':                  { majorCode: 'BMKT', programCode: '1835', classLevel: 'Sophomore', isTransfer: false, studiedAbroad: false, minor: null },
  '5X_X_BUAD.txt':                  { majorCode: 'BLDR', programCode: '1834', classLevel: 'Junior', isTransfer: false, studiedAbroad: false, minor: 'Music Production' },
  '6X_X_BUAD.txt':                  { majorCode: 'BMKT', programCode: '1835', classLevel: 'Senior', isTransfer: false, studiedAbroad: false, isStudentAthlete: true },
  '7X_X_BUAD.txt':                  { majorCode: 'BUAD', programCode: '486',  classLevel: 'Junior', isTransfer: false, studiedAbroad: false, minor: 'Applied Analytics' },
  '8Transfer_X_BUAD.txt':           { majorCode: 'BEI',  programCode: '1832', classLevel: 'Senior', isTransfer: true, studiedAbroad: false, minor: null },
  '9X_StudyAbroad_BUAD.txt':        { majorCode: 'BFIN', programCode: '1833', classLevel: 'Senior', isTransfer: false, studiedAbroad: true, minor: 'Legal Studies' },
  '10X_X_WBB.txt':                  { majorCode: 'BUSW', programCode: '1485', classLevel: 'Sophomore', isTransfer: false, studiedAbroad: false, minor: null },
};

let passed = 0, failed = 0;

for (const file of files) {
  const text = fs.readFileSync(path.join(dir, file), 'utf-8');
  const r = parseStarsFields(text);
  const exp = expected[file] || {};

  const checks = [
    ['majorCode',        r.majorCode,        exp.majorCode],
    ['programCode',      r.programCode,      exp.programCode],
    ['classLevel',       r.classLevel,       exp.classLevel],
    ['isTransfer',       r.isTransfer,       exp.isTransfer],
    ['studiedAbroad',    r.studiedAbroad,    exp.studiedAbroad],
    ['minor',            r.minor,            exp.minor],
  ];

  const failures = checks.filter(([,got,want]) => want !== undefined && String(got) !== String(want));

  console.log(`\n${file.replace('.txt','')}`);
  console.log(`  major: "${r.major}"  concentration: "${r.concentration}"  gpa: ${r.gpa}  catalogYear: ${r.catalogYear}`);
  console.log(`  completed: ${r.completedCourses.length}  inProgress: ${r.inProgressCourses.length}  transferUnits: ${r.transferUnits}`);

  if (failures.length === 0) {
    console.log(`  PASS (${checks.length}/${checks.length} checks)`);
    passed++;
  } else {
    failures.forEach(([field, got, want]) => console.log(`  FAIL ${field}: got "${got}", expected "${want}"`));
    failed++;
  }
}

console.log(`\n${'='.repeat(50)}`);
console.log(`Result: ${passed}/${passed+failed} files fully passing`);
