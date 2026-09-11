# Repository notes for Claude

Module-specific rules live in the sections below. A section applies only to the
folder it names.

## degree-planner/ only

These rules apply to `degree-planner/` and to no other folder in this repo.

- Client-side only. No API routes, server actions, analytics, or third-party scripts. Student data stays in the browser.
- Static export only. Nothing platform-specific, so the build deploys unchanged to Vercel or Netlify.
- `src/data/parseStarsReport.ts` and `src/data/analyzePlan.ts` are stubs that ignore their arguments and return fixed objects. Don't add degree logic anywhere in this app.
- Mark anything invented with a `GAP(stars|analysis|catalogue|other)` comment and leave it in place.
- `npm run check:privacy` enforces the first two rules; `npm test` enforces the third.
