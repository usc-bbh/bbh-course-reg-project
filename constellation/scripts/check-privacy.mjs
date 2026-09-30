// Fails if Constellation could leak a student's report. Run by npm test, after npm run build.
//   1. Git: no report or anything derived from one is tracked or staged (test/samples/,
//      test/expected/, any PDF). .gitignore alone is not enough; a force-add gets past it.
//   2. Source: no URLs, network APIs, or browser storage in src/. The page reads the PDF,
//      renders it, and forgets it.
//   3. Built page: index.html carries the Content-Security-Policy that blocks every request,
//      and loads nothing from outside itself.
// Usage: npm run check:privacy
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const problems = [];

// 1. Git
let tracked = null;
try { tracked = execFileSync('git', ['ls-files', '--cached', '--', '.'], { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).split('\n').filter(Boolean); }
catch { console.log('skip  git check (not a git checkout)'); }
if (tracked) {
  for (const f of tracked) {
    if (/^test\/(samples|expected)\//.test(f) && !f.endsWith('/.keep')) problems.push(`git tracks ${f}. Reports and results derived from them must never be committed.`);
    else if (/\.pdf$/i.test(f)) problems.push(`git tracks ${f}. PDFs must never be committed.`);
  }
}

// 2. Source
const NETWORK = [
  [/\b(?:https?:)?\/\/[a-z0-9-]+\.[a-z]/i, 'a URL'],
  [/\bfetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|RTCPeerConnection/, 'a network API'],
  [/localStorage|sessionStorage|indexedDB|document\.cookie|caches\./, 'browser storage'],
  [/<(?:script|link|iframe|img|object|embed)\b[^>]*\b(?:src|href)=/i, 'an external resource tag']
];
for (const f of fs.readdirSync(path.join(root, 'src'))) {
  const text = fs.readFileSync(path.join(root, 'src', f), 'utf8');
  for (const [re, what] of NETWORK) if (re.test(text)) problems.push(`src/${f} contains ${what} (${text.match(re)[0]}). The page must make no requests and store nothing.`);
}

// 3. Built page
const indexPath = path.join(root, 'index.html');
if (!fs.existsSync(indexPath)) problems.push('index.html is missing. Run npm run build.');
else {
  const page = fs.readFileSync(indexPath, 'utf8');
  const csp = page.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)">/);
  if (!csp) problems.push('index.html has no Content-Security-Policy. Run npm run build.');
  else {
    for (const rule of ["default-src 'none'", "connect-src 'none'", "form-action 'none'"])
      if (!csp[1].includes(rule)) problems.push(`index.html CSP is missing ${rule}.`);
    if (/unsafe-inline'[^;]*;/.test(csp[1].match(/script-src[^;]*;/)?.[0] || '') || /script-src[^;]*(https?:|\*)/.test(csp[1]))
      problems.push('index.html CSP allows scripts other than the page\'s own.');
    if (page.indexOf(csp[0]) > page.search(/<script|<style/)) problems.push('index.html CSP must come before the first <style> or <script>.');
  }
  const ext = page.match(/<(?:script|link|iframe|img|object|embed)\b[^>]*\b(?:src|href)=["']?(?!data:|#)[^"'\s>]+|@import|url\(\s*["']?(?:https?:)?\/\//i);
  if (ext) problems.push(`index.html loads something from outside itself: ${ext[0].slice(0, 80)}`);
}

if (problems.length) {
  console.log(`FAIL  privacy check\n${problems.map(p => '  - ' + p).join('\n')}`);
  process.exit(1);
}
console.log('PASS  privacy check (nothing tracked, no requests, no storage)');
