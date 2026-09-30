// Builds index.html from src/page.html. Everything the page needs is inlined: the parser, the
// PDF text extraction, pdf.js and its worker (bundled from node_modules), and the sample
// report. Text is set in Times New Roman, which is already on the device. The result makes no
// network requests, and its Content-Security-Policy says so.
// Usage: npm install && npm run build
const fs = require('fs');
const crypto = require('crypto');
const esbuild = require('esbuild');

const read = f => fs.readFileSync(f, 'utf8');
const nm = f => require.resolve(f);

// pdf.js main library as a plain script exposing window.pdfjsLib, and its worker as a string the
// page turns into a blob. Same pdfjs-dist version (pinned in package.json) that npm test uses.
const bundle = (entry, globalName) => esbuild.buildSync({
  entryPoints: [nm(entry)], bundle: true, format: 'iife', globalName, minify: true,
  platform: 'browser', target: 'es2020', write: false, logLevel: 'error',
  define: { 'import.meta.url': '""' }
}).outputFiles[0].text;
const pdfjs = bundle('pdfjs-dist/legacy/build/pdf.mjs', 'pdfjsLib');
const worker = bundle('pdfjs-dist/legacy/build/pdf.worker.mjs');

// Inline scripts end at the first "</script"; escape it anywhere it appears in inlined code.
const safe = s => s.replace(/<\/script/gi, '<\\/script').replace(/<!--/g, '<\\!--');
const str = s => safe(JSON.stringify(s));

const parts = {
  '/*PARSER*/': safe(read('src/parser.js')),
  '/*PDFTEXT*/': safe(read('src/pdftext.js')),
  '/*PDFJS*/': safe(pdfjs),
  '/*PDFWORKER*/': str(worker),
  '/*SAMPLE*/': str(read('src/sample-report.txt'))
};
let page = read('src/page.html');
for (const [mark, value] of Object.entries(parts)) {
  if (!page.includes(mark)) throw new Error(`src/page.html is missing ${mark}`);
  page = page.replace(mark, () => value); // function form: code contains "$&" and friends
}

// Content-Security-Policy: no connections, no remote anything. Scripts allowed only by hash, so
// an injected or edited script without a rebuild will not run. Workers only from blob: (pdf.js).
const hashes = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(m => `'sha256-${crypto.createHash('sha256').update(m[1]).digest('base64')}'`);
const csp = [
  "default-src 'none'", `script-src ${hashes.join(' ')}`, 'worker-src blob:', 'child-src blob:',
  "style-src 'unsafe-inline'", 'img-src data: blob:', "connect-src 'none'",
  "form-action 'none'", "base-uri 'none'"
].join('; ');
page = page.replace('<!--CSP-->', `<meta http-equiv="Content-Security-Policy" content="${csp}">`);

fs.writeFileSync('index.html', page);
console.log(`Built index.html (${(page.length / 1024).toFixed(0)} KB, ${hashes.length} inline scripts)`);
