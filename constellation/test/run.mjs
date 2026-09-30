// Runs every PDF in test/samples/ through the same code as the page: src/pdftext.js (with the
// pdfjs-dist version pinned in package.json, the one build.js bundles) -> src/parser.js.
// For each report it:
//   1. checks redaction: the name, student ID, and diploma/mailing block must not appear anywhere
//      in the parsed result or in the "original report text" the page shows;
//   2. compares a summary against test/expected/<name>.json, or writes a draft to check by hand.
// Usage: npm install && npm test
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';

const require = createRequire(import.meta.url);
const P = require('../src/parser.js');
const { extractText } = require('../src/pdftext.js');
const here = path.dirname(fileURLToPath(import.meta.url));
const samples = path.join(here, 'samples');
const expected = path.join(here, 'expected');

// What redaction must remove, read from the unredacted text: the name on the "STARS Report for"
// line, any 10-digit ID, and each line of the diploma information block (name and address).
function secrets(raw) {
  const out = new Set();
  const lines = raw.replace(/\r/g, '').split('\n');
  for (const l of lines) {
    const m = l.match(/STARS Report for\s+(.+?)(?:\s{2,}|\s+ID#|$)/i);
    if (m) out.add(m[1].trim());
    for (const id of l.match(/\b\d{10}\b/g) || []) out.add(id);
  }
  const d = lines.findIndex(l => /USC Diploma Information/i.test(l));
  if (d >= 0) for (let i = d + 1; i < lines.length && !/^\s*={10,}/.test(lines[i]); i++) out.add(lines[i].trim());
  // Anonymized reports replace details with X's; those are not secrets and match too broadly.
  return [...out].filter(s => /[A-Za-z0-9]/.test(s) && s.length > 3 && !/^[X\s.,-]+$/.test(s));
}

const files = fs.readdirSync(samples).filter(f => f.toLowerCase().endsWith('.pdf'));
if (!files.length) {
  console.log('No PDFs in test/samples/. Add the anonymized reports there (never commit them).');
  process.exit(0);
}

let failed = 0;
for (const f of files) {
  let raw, r;
  try {
    raw = await extractText(pdfjs, new Uint8Array(fs.readFileSync(path.join(samples, f))));
    r = P.parse(raw);
  } catch (e) { failed++; console.log(`ERROR ${f}: ${e.message}`); continue; }

  const shown = JSON.stringify(r) + '\n' + P.redact(raw).text;
  const leaks = secrets(raw).filter(s => shown.includes(s));
  if (leaks.length) { failed++; console.log(`LEAK  ${f}: ${leaks.length} redacted value(s) still appear in the output`); continue; }

  const summary = {
    major: r.meta.major,
    catalogYear: r.meta.catalogYear,
    gpa: r.gpa,
    majorGpa: r.majorGpa,
    units: r.units ? { earned: r.units.earned || '', inProcess: r.units.inProcess || '', needs: r.units.needs || '' } : null,
    redacted: [...r.redacted].sort(),
    courses: r.courseList.length,
    blocks: r.blocks.map(b => ({ name: b.name, status: b.status, subs: b.subs.map(s => s.status) })),
    left: r.left.map(l => `${l.area} | ${l.count} ${l.unit} | ${l.label}`)
  };

  const base = path.join(expected, f.replace(/\.pdf$/i, ''));
  if (fs.existsSync(base + '.json')) {
    const ok = JSON.stringify(JSON.parse(fs.readFileSync(base + '.json', 'utf8'))) === JSON.stringify(summary);
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${f}`);
    if (!ok) { failed++; fs.writeFileSync(base + '.actual.json', JSON.stringify(summary, null, 2)); }
  } else {
    fs.writeFileSync(base + '.draft.json', JSON.stringify(summary, null, 2));
    console.log(`NEW   ${f}  (wrote ${path.basename(base)}.draft.json; check it against the PDF, then rename to .json)`);
  }
}
process.exit(failed ? 1 : 0);
