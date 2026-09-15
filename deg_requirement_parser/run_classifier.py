#!/usr/bin/env python3
"""
Classify USC degree-requirement text into constraint records.

Reads one scraped programme .txt, fills prompt_v1.txt with the taxonomy and the
requirement text, calls the Claude API, and writes the raw response plus the
parsed JSON to out/.

Usage
    export ANTHROPIC_API_KEY=...
    python run_classifier.py --limit 1          # one file, prove it works
    python run_classifier.py                    # the full 15-file test set
    python run_classifier.py --dry-run          # build prompts, call nothing

Run --dry-run first. It writes the exact prompt to out/ so you can read what the
model will actually receive before spending anything.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

# --- Paths -------------------------------------------------------------------
# Francis's scraper folder is still named catalogue_scraper. It is due to be
# renamed to degree_requirements_scraper. Keep that path here, in one place.

REPO = Path(__file__).resolve().parent.parent
PROGRAMS_DIR = (
    REPO
    / "catalogue_scraper"
    / "data"
    / "usc_undergrad_complete_catalogue_2026_2027"
    / "programs"
)
PROMPT_PATH = REPO / "docs" / "prompt_v1.txt"
TAXONOMY_PATH = Path(__file__).resolve().parent / "constraint_taxonomy.md"
HERE = Path(__file__).resolve().parent

# --- Model and budget --------------------------------------------------------
# Confirm the model id against your console before a real run:
#   python run_classifier.py --list-models
DEFAULT_MODEL = "claude-sonnet-5"
MAX_OUTPUT_TOKENS = 8000

# Dollars per million tokens, (input, output), per model. This only drives the
# local cost printout and the --budget guard, not billing. Source:
# https://platform.claude.com/docs/en/models/overview (checked 2026-09-15).
# A model not listed here needs --price-in and --price-out on the command line.
MODEL_PRICES = {
    "claude-fable-5-1": (10.00, 50.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-5": (3.00, 15.00),
}


def model_prices(model: str) -> tuple[float, float] | None:
    """Exact id first, then the longest listed id that prefixes it (dated ids)."""
    if model in MODEL_PRICES:
        return MODEL_PRICES[model]
    matches = [k for k in MODEL_PRICES if model.startswith(k)]
    return MODEL_PRICES[max(matches, key=len)] if matches else None

# The 15 programmes named in docs/catalogue-classifier-brief.md.
TEST_SET = [
    "025_astronomy_ba",
    "042_business_administration_bs",
    "079_cognitive_science_ba",
    "086_computer_science_bs",
    "102_economics_ba",
    "120_global_health_studies_bs",
    "124_history_ba",
    "134_interdisciplinary_studies_ba",
    "141_journalism_ba",
    "162_occupational_therapy_bs",
    "169_performance_violin_viola_violoncello_double_bass_or_bm",
    "183_public_policy_bs",
    "192_social_work_bsw",
    "399_natural_science_minor",
    "458_statistics_minor",
]

DEGREE_WORDS = {
    "ba": "BA", "bs": "BS", "bfa": "BFA", "bm": "BM", "barch": "BArch",
    "bsw": "BSW", "minor": "Minor", "bse": "BSE",
}


def program_name_from_stem(stem: str) -> str:
    """025_astronomy_ba -> 'Astronomy BA'.

    Filename-derived, so eyeball the first few. If they read badly, switch to
    the `name` column of data/.../index.csv instead.
    """
    parts = stem.split("_")[1:]  # drop the leading number
    if not parts:
        return stem
    if parts[-1] in DEGREE_WORDS:
        degree = DEGREE_WORDS[parts[-1]]
        words = parts[:-1]
    else:
        degree = ""
        words = parts
    title = " ".join(w.capitalize() for w in words)
    return f"{title} {degree}".strip()


def build_prompt(template: str, taxonomy: str, name: str, requirements: str) -> str:
    required = ["{{TAXONOMY}}", "{{PROGRAM_NAME}}", "{{REQUIREMENTS}}"]
    missing = [p for p in required if p not in template]
    if missing:
        raise SystemExit(
            f"{PROMPT_PATH} is missing placeholder(s): {', '.join(missing)}.\n"
            "Open the file and check the exact spelling, then fix `required` here."
        )
    return (
        template.replace("{{TAXONOMY}}", taxonomy)
        .replace("{{PROGRAM_NAME}}", name)
        .replace("{{REQUIREMENTS}}", requirements)
    )


def extract_json(text: str):
    """Pull the JSON object out of a response that may be fenced or padded."""
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidate = fence.group(1) if fence else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in response")
    return json.loads(candidate[start : end + 1])


def call_api(client, model: str, prompt: str, attempts: int = 4):
    delay = 4
    for attempt in range(1, attempts + 1):
        try:
            return client.messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001
            transient = any(
                s in type(exc).__name__.lower() or s in str(exc).lower()
                for s in ("overloaded", "rate", "timeout", "connection", "529", "500")
            )
            if attempt == attempts or not transient:
                raise
            print(f"    retry {attempt}/{attempts - 1} after {delay}s ({type(exc).__name__})")
            time.sleep(delay)
            delay *= 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, help="only the first N programmes")
    ap.add_argument("--only", nargs="*", help="specific stems, e.g. 025_astronomy_ba")
    ap.add_argument("--all", action="store_true", help="every programme, not just the 15 (costs real money)")
    ap.add_argument("--dry-run", action="store_true", help="write prompts, call nothing")
    ap.add_argument("--force", action="store_true", help="redo programmes that already have output")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--budget", type=float, default=50.0, help="stop before exceeding this many dollars")
    ap.add_argument("--list-models", action="store_true", help="print available model ids and exit")
    ap.add_argument("--out-dir", default="out",
                    help="output folder inside deg_requirement_parser, e.g. out_sonnet5 (default: out)")
    ap.add_argument("--price-in", type=float, help="input $/million tokens, for a model not in MODEL_PRICES")
    ap.add_argument("--price-out", type=float, help="output $/million tokens, for a model not in MODEL_PRICES")
    args = ap.parse_args()

    if args.list_models:
        from anthropic import Anthropic

        for m in Anthropic().models.list().data:
            print(m.id)
        return 0

    for path in (PROMPT_PATH, TAXONOMY_PATH):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1
    if not PROGRAMS_DIR.is_dir():
        print(f"missing programmes folder: {PROGRAMS_DIR}", file=sys.stderr)
        print("Has catalogue_scraper been renamed? Update PROGRAMS_DIR.", file=sys.stderr)
        return 1

    out_dir = HERE / args.out_dir
    out_label = args.out_dir.rstrip("/")

    prices = model_prices(args.model)
    if args.price_in is not None and args.price_out is not None:
        prices = (args.price_in, args.price_out)
    if prices is None and not args.dry_run:
        print(f"No price known for model '{args.model}'.", file=sys.stderr)
        print("Add it to MODEL_PRICES or pass --price-in and --price-out.", file=sys.stderr)
        return 1
    price_in, price_out = prices or (0.0, 0.0)
    if not args.dry_run:
        print(f"Model {args.model} at ${price_in:g} in / ${price_out:g} out per million tokens. "
              f"Output folder: {out_label}/\n")

    template = PROMPT_PATH.read_text(encoding="utf-8")
    taxonomy = TAXONOMY_PATH.read_text(encoding="utf-8")

    if args.only:
        stems = args.only
    elif args.all:
        stems = sorted(p.stem for p in PROGRAMS_DIR.glob("*.txt"))
    else:
        stems = TEST_SET
    if args.limit:
        stems = stems[: args.limit]

    out_dir.mkdir(parents=True, exist_ok=True)

    client = None
    if not args.dry_run:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY is not set. export it first.", file=sys.stderr)
            return 1
        from anthropic import Anthropic

        client = Anthropic()

    spent = 0.0
    rows = []
    failures = 0

    for i, stem in enumerate(stems, 1):
        src = PROGRAMS_DIR / f"{stem}.txt"
        if not src.exists():
            print(f"[{i}/{len(stems)}] {stem}: SKIP, no such file")
            failures += 1
            continue

        json_path = out_dir / f"{stem}.json"
        if json_path.exists() and not args.force and not args.dry_run:
            print(f"[{i}/{len(stems)}] {stem}: already done, use --force to redo")
            continue

        name = program_name_from_stem(stem)
        requirements = src.read_text(encoding="utf-8")
        prompt = build_prompt(template, taxonomy, name, requirements)

        if args.dry_run:
            (out_dir / f"{stem}.prompt.txt").write_text(prompt, encoding="utf-8")
            approx = len(prompt) // 4
            print(f"[{i}/{len(stems)}] {stem}: prompt {len(prompt):,} chars (~{approx:,} tokens) -> {out_label}/{stem}.prompt.txt")
            continue

        print(f"[{i}/{len(stems)}] {stem} ({name}) ...", flush=True)
        try:
            resp = call_api(client, args.model, prompt)
        except Exception as exc:  # noqa: BLE001
            print(f"    API ERROR: {type(exc).__name__}: {exc}")
            failures += 1
            continue

        text = "".join(block.text for block in resp.content if block.type == "text")
        (out_dir / f"{stem}.response.txt").write_text(text, encoding="utf-8")

        cost = (
            resp.usage.input_tokens / 1e6 * price_in
            + resp.usage.output_tokens / 1e6 * price_out
        )
        spent += cost

        try:
            data = extract_json(text)
        except Exception as exc:  # noqa: BLE001
            print(f"    UNPARSEABLE: {exc}. Raw response kept at {out_label}/{stem}.response.txt")
            failures += 1
        else:
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            n = len(data.get("constraints", []))
            u = len(data.get("unclassified", []))
            print(f"    ok: {n} constraints, {u} unclassified, status={data.get('status')}, ${cost:.3f}")

        rows.append(
            {
                "stem": stem,
                "model": args.model,
                "in_tokens": resp.usage.input_tokens,
                "out_tokens": resp.usage.output_tokens,
                "cost_usd": round(cost, 4),
            }
        )

        if spent >= args.budget:
            print(f"\nStopping: spent ${spent:.2f}, at the ${args.budget:.2f} budget.")
            break

    if rows:
        with (out_dir / "run_log.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\nSpent ${spent:.2f} across {len(rows)} call(s). Log: {out_label}/run_log.csv")
    if failures:
        print(f"{failures} programme(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
