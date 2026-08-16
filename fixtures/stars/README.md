# Shared STARS fixtures

These files sit on the seam between the **parser** (`stars-parser/`, JavaScript)
and the **validator** (`validator/`, Python). They are owned by neither module
so both can depend on them without a circular relationship.

The contract, per sample student:

```
<name>.txt     extracted STARS text  — the parser's INPUT
<name>.json    parsed STARS summary  — the parser's expected OUTPUT
                                       AND the validator's stars_summary INPUT
```

- The parser test asserts that parsing `<name>.txt` produces exactly `<name>.json`.
- The validator test loads `<name>.json` as its `stars_summary`.

Same bytes on both sides. If the parser's output shape drifts, a validator test
breaks immediately instead of surfacing as a broken app weeks later, and adding
one new sample student exercises both modules at once.

## Current contents

- `mock_stars_report.json` — a hand-written stub kept for validator edge cases
  the real redacted samples don't happen to cover. It has no matching `.txt`
  yet; the parser side may add one, or it may stay a validator-only case.

Redaction of real STARS PDFs happens in the separate internal redactor tool
(see the root README); redacted samples land here as `<name>.txt` / `<name>.json`
pairs.
