# deg_requirement_parser

Module 4A, first stage. Turns USC's prose degree requirements into structured constraint
records that the degree-plan engine can solve over.

## What's here

| File | What it is |
|---|---|
| `constraint_taxonomy.md` | The taxonomy: five constraint families, each with a description, its `details` shape, and real catalogue sentences paired with their JSON encoding. Fills the `{{TAXONOMY}}` placeholder in `docs/prompt_v1.txt`. |
| `run_classifier.py` | Reads a scraped programme `.txt`, builds the prompt, calls the Claude API, writes the raw response and the parsed JSON to `out/`. |
| `check_results.py` | Validates the output and writes `out/summary.csv`. |
| `out/` | Generated. Raw responses, parsed JSON, run log, summary. |

## Input and output

Input is Francis's catalogue scrape:
`catalogue_scraper/data/usc_undergrad_complete_catalogue_2026_2027/programs/*.txt`

Output per programme:
`out/<stem>.response.txt` (raw) and `out/<stem>.json` (parsed).

## Running it

```bash
export ANTHROPIC_API_KEY=...           # never commit this
pip install anthropic

python run_classifier.py --dry-run     # build prompts, call nothing
python run_classifier.py --limit 1     # one programme, end to end
python run_classifier.py               # the 15-programme test set
python check_results.py                # validate, write out/summary.csv
```

`--budget` stops the run before it exceeds a dollar figure, default 50. Programmes that already
have output are skipped unless you pass `--force`.

## Tuning

When a programme comes back wrong, fix it by adding the failing sentence to
`constraint_taxonomy.md` as a new example under the right family, not by adding rules to the
prompt. Change one thing at a time and keep the previous prompt version so the comparison is
real.

## Known limitations

- `PROGRAMS_DIR` in both scripts hardcodes `catalogue_scraper/`. That folder is due to be
  renamed to `degree_requirements_scraper`; it is one constant at the top of each file.
- Programme names are derived from filenames. If any read badly, switch to the `name` column of
  the scraper's `index.csv`.
- The classifier is called as a plain message and the JSON is extracted from the response text.
  Binding a generated JSON Schema to a tool call would enforce the shape rather than check it
  afterwards; `check_results.py` covers the gap for now.
