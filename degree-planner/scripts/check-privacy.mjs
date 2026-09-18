#!/usr/bin/env node
/**
 * The privacy and platform guardrail.
 *
 * A manual grep is a one-time result. This is the version the next person
 * inherits: `npm run check:privacy` fails the moment anything in this app can
 * reach the network, run on a server, or read the environment.
 *
 * Exactly one file is allowed to make a network request — src/data/catalogue.ts,
 * which fetches public course data and nothing else.
 *
 * The deploy configs are checked too. A serverless function added through
 * vercel.json or netlify.toml would never show up in a scan of src/, so the
 * blocks that could introduce one are rejected here.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const appRoot = fileURLToPath(new URL('..', import.meta.url));
const sourceRoot = join(appRoot, 'src');

/** The one module allowed to touch the network. */
const NETWORK_ALLOWLIST = ['src/data/catalogue.ts'];

const FORBIDDEN = [
  { pattern: /\bfetch\s*\(/, label: 'fetch(', network: true },
  { pattern: /\bXMLHttpRequest\b/, label: 'XMLHttpRequest', network: true },
  { pattern: /\bsendBeacon\b/, label: 'navigator.sendBeacon', network: true },
  { pattern: /\bnew\s+WebSocket\b/, label: 'new WebSocket', network: true },
  { pattern: /\bnew\s+EventSource\b/, label: 'EventSource', network: true },
  { pattern: /<script\s+src=/i, label: '<script src=', network: true },
  { pattern: /['"]use server['"]/, label: '"use server"', network: false },
  { pattern: /from\s+['"]next\/headers['"]/, label: 'next/headers', network: false },
  { pattern: /\bprocess\.env\b/, label: 'process.env', network: false },
  { pattern: /\bimport\.meta\.env\b/, label: 'import.meta.env', network: false },
  // The test suite runs in Node and needs @types/node, which is declared once
  // in tsconfig and therefore also visible to src/. These three keep that from
  // becoming a way for Node to leak into the browser half of the app.
  { pattern: /from\s+['"]node:/, label: 'an import from node:', network: false },
  { pattern: /\bprocess\s*\./, label: 'the Node process global', network: false },
  { pattern: /\b__dirname\b|\b__filename\b/, label: 'a Node path global', network: false },
];

/** Server-side or platform-specific files that must not exist at all. */
const FORBIDDEN_PATHS = [
  /(^|\/)api\//,
  /(^|\/)middleware\.(t|j)sx?$/,
  /(^|\/)route\.(t|j)sx?$/,
  /(^|\/)server\.(t|j)sx?$/,
  /\.server\.(t|j)sx?$/,
  /(^|\/)netlify\/functions\//,
  /(^|\/)vercel\/functions\//,
];

const ANALYTICS_DEPENDENCIES = [
  '@vercel/analytics',
  '@vercel/speed-insights',
  '@netlify/plugin-nextjs',
  'posthog-js',
  'mixpanel-browser',
  '@sentry/react',
  '@sentry/browser',
  '@sentry/nextjs',
  'react-ga',
  'react-ga4',
  'logrocket',
  'hotjar',
  '@datadog/browser-rum',
  'amplitude-js',
  '@amplitude/analytics-browser',
  'bugsnag-js',
  '@bugsnag/js',
];

const SOURCE_EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.html', '.css']);

const problems = [];

function walk(directory) {
  const files = [];
  for (const entry of readdirSync(directory)) {
    const full = join(directory, entry);
    if (statSync(full).isDirectory()) files.push(...walk(full));
    else files.push(full);
  }
  return files;
}

function repoPath(absolute) {
  return relative(appRoot, absolute).split(sep).join('/');
}

/** A line that only talks about a rule is not a violation of it. */
function stripComment(line) {
  return line.replace(/^\s*(\/\/|\*|\/\*|<!--).*$/, '');
}

/* ── 1. Source scan ─────────────────────────────────────────────────────── */

const sourceFiles = [...walk(sourceRoot), join(appRoot, 'index.html')];

for (const file of sourceFiles) {
  const shown = repoPath(file);
  const extension = shown.slice(shown.lastIndexOf('.'));
  if (!SOURCE_EXTENSIONS.has(extension)) continue;

  if (FORBIDDEN_PATHS.some((pattern) => pattern.test(shown))) {
    problems.push(`${shown}: this path is a server or platform entry point, which this app must not have.`);
    continue;
  }

  const lines = readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, index) => {
    const code = stripComment(line);
    for (const rule of FORBIDDEN) {
      if (!rule.pattern.test(code)) continue;
      if (rule.network && NETWORK_ALLOWLIST.includes(shown)) continue;
      problems.push(`${shown}:${index + 1}: found ${rule.label}`);
    }
  });
}

/* ── 2. The allowlisted file must still be the only one reaching out ────── */

for (const allowed of NETWORK_ALLOWLIST) {
  const absolute = join(appRoot, allowed);
  try {
    const hits = readFileSync(absolute, 'utf8')
      .split('\n')
      .map(stripComment)
      .filter((line) => /\bfetch\s*\(/.test(line));
    if (hits.length > 1) {
      problems.push(`${allowed}: ${hits.length} network calls. Keep the catalogue to a single request.`);
    }
  } catch {
    problems.push(`${allowed}: allowlisted for network access but missing.`);
  }
}

/* ── 3. Dependencies ────────────────────────────────────────────────────── */

const manifest = JSON.parse(readFileSync(join(appRoot, 'package.json'), 'utf8'));
const declared = {
  ...(manifest.dependencies ?? {}),
  ...(manifest.devDependencies ?? {}),
  ...(manifest.optionalDependencies ?? {}),
};
for (const name of Object.keys(declared)) {
  if (ANALYTICS_DEPENDENCIES.includes(name)) {
    problems.push(`package.json: ${name} is an analytics, telemetry or platform-adapter dependency.`);
  }
}

/* ── 4. Deploy configs ──────────────────────────────────────────────────── */

/**
 * Both files may describe a static build and its headers. Neither may describe
 * a server: no functions, no cron jobs, no build plugins, no build-time
 * environment. A deploy config is the one place those could be added without
 * touching a single line of src/.
 */
const DEPLOY_CONFIGS = [
  {
    file: 'vercel.json',
    forbidden: [
      { pattern: /"functions"\s*:/, label: 'a "functions" block' },
      { pattern: /"crons"\s*:/, label: 'a "crons" block' },
      { pattern: /"env"\s*:/, label: 'an "env" block' },
      { pattern: /"middleware"/, label: 'middleware' },
      { pattern: /@vercel\//, label: 'a @vercel/* package' },
      { pattern: /\/api\//, label: 'an /api/ route' },
    ],
  },
  {
    file: 'netlify.toml',
    forbidden: [
      { pattern: /^\s*\[functions/m, label: 'a [functions] block' },
      { pattern: /^\s*\[\[edge_functions/m, label: 'an [[edge_functions]] block' },
      { pattern: /^\s*\[\[plugins/m, label: 'a [[plugins]] block' },
      { pattern: /^\s*\[build\.environment/m, label: 'a [build.environment] block' },
      { pattern: /\/\.netlify\/functions\//, label: 'a function endpoint' },
    ],
  },
];

let deployConfigsSeen = 0;

for (const config of DEPLOY_CONFIGS) {
  let contents;
  try {
    contents = readFileSync(join(appRoot, config.file), 'utf8');
  } catch {
    // Neither file has to exist. Only its contents are constrained.
    continue;
  }
  deployConfigsSeen += 1;
  const lines = contents.split('\n');
  lines.forEach((line, index) => {
    const code = stripComment(line.replace(/^\s*#.*$/, ''));
    for (const rule of config.forbidden) {
      if (rule.pattern.test(code)) {
        problems.push(`${config.file}:${index + 1}: found ${rule.label}, which would give this app a server half.`);
      }
    }
  });
}

/* ── 5. Report ──────────────────────────────────────────────────────────── */

if (problems.length > 0) {
  console.error('Privacy and platform check FAILED:\n');
  for (const problem of problems) console.error(`  ${problem}`);
  console.error(
    '\nStudent data never leaves the browser, and the build stays a plain static front end.',
  );
  console.error('If a new network call is genuinely needed, it belongs in src/data/catalogue.ts.');
  process.exit(1);
}

console.log(
  `Privacy and platform check passed (${sourceFiles.length} source files, ${deployConfigsSeen} deploy configs scanned).`,
);
console.log(`Network access is limited to: ${NETWORK_ALLOWLIST.join(', ')}`);
