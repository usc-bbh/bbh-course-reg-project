#!/bin/bash
# Runs in a visible Terminal window. Args: YEAR CATOID  (or: LATEST auto)
# Collects one text file per standalone undergraduate degree program for the
# chosen USC catalogue year into a 'USC Catalogue Text Files' folder beside the app
# (override with USC_COLLECTOR_BASE).
set -u
RES="$(cd "$(dirname "$0")" && pwd)"
SCRAPER="$RES/scraper"
APP_HOME="$(cd "$RES/../../.." && pwd)"   # the folder that holds this .app
BASE="${USC_COLLECTOR_BASE:-$APP_HOME/USC Complete Text Files}"
PROFILE="$BASE/browser_profile"
YEAR="${1:-LATEST}"
CATOID="${2:-auto}"
EXTRA=("${@:3}")   # optional passthrough (e.g. --max-programs N for smoke tests)

fail() {
    echo ""
    echo "STOPPED: $1"
    echo "It is safe to run the app again — completed programs are never re-downloaded."
    read -n 1 -s -r -p "Press any key to close this window..."
    echo ""
    exit 1
}

echo "==============================================="
echo " USC Complete Collector — ${YEAR}"
echo "==============================================="
mkdir -p "$BASE" "$PROFILE"
cd "$SCRAPER" || fail "app files are missing"

# Environment: build or repair automatically.
IMPORT_CHECK='import pathlib, usc_catalog_scraper as m; assert pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd().resolve())'
if ! .venv/bin/python -c "$IMPORT_CHECK" >/dev/null 2>&1; then
    echo "First run: setting up the environment (a few minutes, one time only)..."
    bash "$RES/app_setup.sh" || fail "environment setup failed (see messages above)"
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# First browser run is visible so a one-time verification page can be
# completed by a human; afterwards the saved session allows headless runs.
if [ -n "$(ls -A "$PROFILE" 2>/dev/null)" ]; then
    MODE=""
    echo "Existing browser session found; running in the background (headless)."
else
    MODE="--headed"
    echo "A browser window will open — leave it alone unless USC asks you to verify."
fi

COMMON=(--resume --all-undergrad --delay-min 1.5 --delay-max 3.5 --workdir "$BASE" --browser-profile-dir "$PROFILE")
if [ "$YEAR" = "LATEST" ]; then
    ARGS=(run "${COMMON[@]}")
else
    echo "Locating the ${YEAR} catalogue's Programs page from USC's official navigation..."
    URL="$(python "$RES/resolve_year.py" "$CATOID" "$YEAR" "$BASE" | tail -n 1)" \
        || fail "could not verify the ${YEAR} catalogue on catalogue.usc.edu"
    [ -n "$URL" ] || fail "could not verify the ${YEAR} catalogue on catalogue.usc.edu"
    echo "Programs page: $URL"
    ARGS=(run "${COMMON[@]}" --no-latest-resolution --start-url "$URL" --catalogue-year "$YEAR")
fi

LOG="$(mktemp -t usc_collector_log)"
run_once() {
    # shellcheck disable=SC2086
    python -m usc_catalog_scraper "${ARGS[@]}" ${EXTRA[@]+"${EXTRA[@]}"} $MODE "$@" 2>&1 | tee "$LOG"
    return "${PIPESTATUS[0]}"
}

# Attempt 1 — the layout every observed catalogue year actually uses: no
# section headings, so bound discovery by the page's own h1 and let the
# classifier decide every link (each exclusion recorded with its reason).
run_once --boundary-heading "Programs, Minors and Certificates" --no-strict
STATUS=$?

# Attempt 2 — a literal section heading, in case USC restructures the page.
if [ $STATUS -ne 0 ] && grep -qi "NOT PROVABLE" "$LOG"; then
    echo ""
    echo "Page layout changed — retrying with strict section-heading discovery."
    run_once
    STATUS=$?
fi

# Attempt 3 — degree-type section headings (the archived 2024-2025 layout).
if [ $STATUS -ne 0 ] && grep -qi "NOT PROVABLE" "$LOG" && grep -q "Bachelor" "$LOG"; then
    echo ""
    echo "Retrying with the \"Bachelor's Degree\" section heading this page uses."
    run_once --boundary-heading "Bachelor's Degree"
    STATUS=$?
fi

# WAF flags occasionally serve a verification page and then clear on their
# own. If the run stopped for verification, cool down briefly and resume —
# visibly (headed) so a real interactive check could be completed by a human.
RESUME_TRIES=0
while [ $STATUS -ne 0 ] && [ $RESUME_TRIES -lt 2 ] && grep -qi "verification" "$LOG"; do
    RESUME_TRIES=$((RESUME_TRIES + 1))
    MODE="--headed"
    echo ""
    echo "USC's bot-protection interrupted the run. Waiting 90 seconds, then"
    echo "resuming automatically (attempt $RESUME_TRIES of 2) with a visible browser..."
    sleep 90
    run_once --boundary-heading "Programs, Minors and Certificates" --no-strict
    STATUS=$?
done

echo ""
OUTDIR="$BASE/usc_undergrad_complete_catalogue_${YEAR//-/_}"
[ -d "$OUTDIR" ] || OUTDIR="$(ls -dt "$BASE"/usc_undergrad_complete_catalogue_* 2>/dev/null | head -1)"

if [ $STATUS -eq 0 ] && [ -n "${OUTDIR:-}" ] && [ -d "$OUTDIR" ]; then
    echo "Verifying the collection (audit)..."
    python -m usc_catalog_scraper audit --workdir "$BASE" --output-dir "$OUTDIR" >/dev/null 2>&1
    COUNT=$(ls "$OUTDIR/programs" 2>/dev/null | grep -c '\.txt$')
    echo ""
    echo "DONE — $COUNT program and minor text files are in:"
    echo "  $OUTDIR/programs"
    [ -n "${USC_COLLECTOR_NO_OPEN:-}" ] || open "$OUTDIR/programs"
elif [ -n "${OUTDIR:-}" ] && [ -d "$OUTDIR" ]; then
    echo "The run stopped early (details above)."
    echo "Run the app again to continue — it resumes where it left off."
    echo "Partial output so far: $OUTDIR"
else
    echo "The run stopped before any output was produced (details above)."
fi

echo ""
read -n 1 -s -r -p "Press any key to close this window..."
echo ""
exit $STATUS
