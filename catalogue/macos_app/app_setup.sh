#!/bin/bash
# One-time environment setup for the app (venv + dependencies + Chromium).
# Same as the project's setup.sh but without the test-suite run, so the first
# double-click gets to work quickly.
set -u
cd "$(dirname "$0")/scraper"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 was not found."
    echo "Install Python 3.10+ from https://www.python.org/downloads/ and try again."
    exit 1
fi
echo "Found $(python3 --version)"

# A moved app bundle breaks the venv's absolute paths; rebuild in that case.
IMPORT_CHECK='import pathlib, usc_catalog_scraper as m; assert pathlib.Path(m.__file__).resolve().is_relative_to(pathlib.Path.cwd().resolve())'
if [ -d .venv ] && ! .venv/bin/python -c "$IMPORT_CHECK" >/dev/null 2>&1; then
    echo "Existing environment is stale (app was moved?); rebuilding..."
    rm -rf .venv
fi

if [ ! -d .venv ]; then
    echo "Creating private Python environment (one-time)..."
    python3 -m venv .venv || { echo "ERROR: could not create .venv"; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip -q
echo "Installing the collector and its dependencies..."
python -m pip install -q -e . || { echo "ERROR: dependency install failed"; exit 1; }
echo "Installing Chromium for the browser layer (cached after the first time)..."
python -m playwright install chromium || {
    echo "WARNING: Chromium install failed; rerun the app later to retry."
}
echo "Setup complete."
