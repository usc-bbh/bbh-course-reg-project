# Four-Year Degree Planner

A browser-only planner: a student gives their situation and a proposed multi-year
plan, and the app says whether that plan reaches a degree and what is missing if
it does not.

This is **not** the Next-Semester Validator (`validator/`). There is no
"can I register for these classes next term" screen here, and there should never
be one.

## Running it

```bash
cd degree-planner
npm install
npm run dev        # local development
npm run build      # production build into dist/
npm run preview    # serve the built dist/ locally
```

| Script | What it does |
| --- | --- |
| `npm run build` | Typecheck, then build the static site into `dist/` |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint over the app |
| `npm test` | Unit and component tests (Vitest + Testing Library) |
| `npm run test:e2e` | End-to-end tests against the production build (Playwright) |
| `npm run check:privacy` | The privacy and platform guardrail (see below) |

## The two rules that shape everything

**1. Student data never leaves the browser.** There is no backend, no analytics,
no third-party script and no runtime font CDN — the three typefaces are
vendored into the bundle by `@fontsource` and the university lockup is inline
SVG, so the page fetches nothing from anywhere. Exactly one module,
`src/data/catalogue.ts`, is allowed to make a network request, and the only
thing it requests is public course data shipped with the build.
`npm run check:privacy` fails if anything else in `src/` gains a `fetch(`, an
`XMLHttpRequest`, a `sendBeacon`, a WebSocket, a `<script src=`, a
`process.env`, a `node:` import or a Node global, or a server or platform entry
point — and it fails if an analytics package appears in `package.json`.

**2. The two data layers are stubs, and they stay stubs.**

- `src/data/parseStarsReport.ts` — the real parser is `stars-parser/`. Abhi
  owns it and Agastya reviews it (`docs/parser-brief.md` §2).
- `src/data/analyzePlan.ts` — the real degree-audit engine is Natalie's
  (`catalogue_scraper/README.md` names her as its owner) and does not exist yet.

Both ignore their arguments and return the same object every time. No
requirement checking, prerequisite rules, offering-term rules, unit-load rules
or report parsing live in this app, in the stubs or anywhere else.
`test/stubs.test.ts` asserts that two materially different plans produce a
deeply equal result, so this is machine-checked rather than a promise.

What the stubs return is not invented either. `test/contracts.test.ts` reads
`fixtures/stars/mock_stars_report.json` off disk and fails if the sample student
drifts from the repo's shared fixture, and the result shape follows
`docs/reference/03-degree-planner-architecture.md`: university and college
verdicts are **reused** from the report and carry its prepared date, major and
minor requirements are **computed**.

Anything invented because nobody had specified it carries a one-line
`GAP(stars|analysis|catalogue|other)` comment at the spot where the invention
happens. `grep -rn "GAP(" src` finds all of them, and
`docs/degree-planner-ui-notes.md` is written from that list.

## Type and brand

The header is built to sit beside USC's own registration pages: the wordmark and
the university lockup in a Caslon, the interface in a humanist sans.

| Role | Face | Used for |
| --- | --- | --- |
| Serif | Libre Caslon Text | The wordmark, the lockup, page and panel headings, the verdict |
| Sans | Source Sans 3 | Everything a student reads or types |
| Mono | Source Code Pro | Course codes, units and counts, so columns line up |

All three are self-hosted. Colour, radii and shadows come from
`validator/validator_gui.jsx` — the exact source value is noted beside each
token in `src/styles/index.css`. There are no arbitrary font sizes in
components: everything uses the named scale in that file.

## Layout

```
src/
  domain/        types.ts is the contract; terms.ts is display arithmetic only
  data/          the two stubs, the catalogue module, the sample student
  state/         one store for situation + plan, versioned persistence, useAnalysis
  features/
    situation/   upload, sample, manual entry, the review form, the summary bar
    plan/        the four-year timeline, course picker, move menu, drag and drop
    audit/       verdict, requirements, warnings, cross-highlighting
    toolbar/     export, import, print, reset, clear
  components/    shared primitives and the status system
```

Components import shapes from `src/domain/types.ts` and never from a stub's
internals, so swapping in a real implementation is an import change in
`src/data/` and nothing else.

## Deploying

The build is a plain static site. Nothing in it needs a server, so the same
`dist/` works on either platform, and both configs are committed so an import
needs no fields typed in by hand.

**Vercel** — set the project's **Root Directory** to `degree-planner` and
import. [`vercel.json`](vercel.json) supplies the framework preset, the build
and install commands, the output directory and the response headers. No
environment variables.

**Netlify** — set the site's **Base directory** to `degree-planner` and deploy.
[`netlify.toml`](netlify.toml) supplies the build command, the publish
directory and the same headers. No environment variables, and no
`@netlify/plugin-nextjs` — this is not a Next.js app and needs no adapter.

Both configs send a `Content-Security-Policy` that allows scripts, styles,
fonts, images and data from the app's own origin and nothing else, with
`form-action 'none'` and `frame-ancestors 'none'`. That is the privacy rule
above restated in a form the browser enforces rather than a promise in a
README. `npm run check:privacy` reads both files and fails if either grows a
`functions`, `edge_functions`, `plugins`, `crons` or build-environment block —
the one way this app could gain a server half without a line of `src/`
changing.
