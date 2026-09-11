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
no third-party script and no runtime font CDN. Exactly one module,
`src/data/catalogue.ts`, is allowed to make a network request, and the only
thing it requests is public course data shipped with the build.
`npm run check:privacy` fails if anything else in `src/` gains a `fetch(`, an
`XMLHttpRequest`, a `sendBeacon`, a WebSocket, a `<script src=`, a
`process.env`, or a server or platform entry point — and it fails if an
analytics package appears in `package.json`.

**2. The two data layers are stubs, and they stay stubs.**

- `src/data/parseStarsReport.ts` — the real parser is `stars-parser/`, which
  Abhi and Agastya own.
- `src/data/analyzePlan.ts` — the real analysis layer does not exist yet.

Both ignore their arguments and return the same object every time. No
requirement checking, prerequisite rules, offering-term rules, unit-load rules
or report parsing live in this app, in the stubs or anywhere else.
`test/stubs.test.ts` asserts that two materially different plans produce a
deeply equal result, so this is machine-checked rather than a promise.

Anything invented because nobody had specified it carries a one-line
`GAP(stars|analysis|catalogue|other)` comment at the spot where the invention
happens. `grep -rn "GAP(" src` finds all of them, and
`docs/degree-planner-ui-notes.md` is written from that list.

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
`dist/` works on either platform.

**Vercel** — Root directory `degree-planner`, framework preset **Vite**, build
command `npm run build`, output directory `dist`, install command `npm install`.
No environment variables.

**Netlify** — Base directory `degree-planner`, build command `npm run build`,
publish directory `degree-planner/dist`. No environment variables, and no
`@netlify/plugin-nextjs` — this is not a Next.js app and needs no adapter.
