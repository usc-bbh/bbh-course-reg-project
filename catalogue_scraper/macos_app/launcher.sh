#!/bin/bash
# USC Complete Collector — app entry point.
# Asks which catalogue year, then runs the collection in a Terminal window.
set -u
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"

/usr/bin/osascript -e 'display notification "Fetching the list of catalogue years from catalogue.usc.edu..." with title "USC Complete Collector"' >/dev/null 2>&1

LIST="$(/usr/bin/env python3 "$RES/pick_year.py" 2>/dev/null || true)"

YEAR=""
CATOID="auto"
if [ -n "$LIST" ]; then
    # Build the AppleScript list: newest first, current year marked.
    ITEMS=""
    DEFAULT_ITEM=""
    while IFS=$'\t' read -r year catoid status; do
        [ -n "$year" ] || continue
        if [ "$status" = "current" ]; then
            label="$year  — current catalogue"
            [ -n "$DEFAULT_ITEM" ] || DEFAULT_ITEM="$label"
        else
            label="$year"
        fi
        ITEMS="$ITEMS, \"$label\""
    done <<< "$LIST"
    ITEMS="${ITEMS#, }"
    [ -n "$DEFAULT_ITEM" ] || DEFAULT_ITEM="$(echo "$LIST" | head -1 | cut -f1)"

    CHOICE="$(/usr/bin/osascript <<OSA 2>/dev/null
set yrs to {$ITEMS}
set pick to choose from list yrs with title "USC Complete Collector" with prompt "Which catalogue year should I collect?

One text file per undergraduate program AND per minor (~470 total) will be saved to the USC Complete Scrape folder (next to this app)." default items {"$DEFAULT_ITEM"}
if pick is false then return ""
return item 1 of pick
OSA
)"
    [ -n "$CHOICE" ] || exit 0   # user pressed Cancel
    YEAR="${CHOICE%%  —*}"
    CATOID="$(echo "$LIST" | awk -F'\t' -v y="$YEAR" '$1==y {print $2; exit}')"
    [ -n "$CATOID" ] || CATOID="auto"
else
    # Could not fetch the list quickly — ask for the year by hand.
    CHOICE="$(/usr/bin/osascript <<'OSA' 2>/dev/null
set d to display dialog "I could not fetch the year list right now.

Type the catalogue year to collect (for example 2026-2027), or leave it as LATEST to auto-detect the newest catalogue." default answer "LATEST" with title "USC Complete Collector" buttons {"Cancel", "Collect"} default button "Collect"
return text returned of d
OSA
)"
    [ -n "$CHOICE" ] || exit 0
    YEAR="$(echo "$CHOICE" | tr -d '[:space:]')"
    [ -n "$YEAR" ] || YEAR="LATEST"
fi

case "$YEAR" in
    LATEST|latest|Latest) YEAR="LATEST"; CATOID="auto" ;;
    *)
        if ! echo "$YEAR" | grep -qE '^[0-9]{4}-[0-9]{4}$'; then
            /usr/bin/osascript -e 'display dialog "That did not look like a catalogue year (expected e.g. 2026-2027)." with title "USC Complete Collector" buttons {"OK"} default button "OK"' >/dev/null 2>&1
            exit 1
        fi
        ;;
esac

# Terminal cannot receive arguments directly, so hand it a tiny runner script.
RUNNER="${TMPDIR:-/tmp}/usc_complete_collector_run.command"
cat > "$RUNNER" <<EOF
#!/bin/bash
exec "$RES/driver.sh" "$YEAR" "$CATOID"
EOF
chmod +x "$RUNNER"
open -a Terminal "$RUNNER"
