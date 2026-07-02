#!/usr/bin/env bash
#
# Assemble the Hugging Face Space bundle from the ONE canonical engine package.
#
# There is a single source of truth for the redaction engine:
#     internal-tools/redaction/redactors/
# This script copies it into hf-space/redactors/ so the Space folder is
# self-contained for upload/push. The copy is git-ignored, so it never lives in
# the repo as a second, drift-prone version.
#
# Run this whenever you're about to deploy (or after the engine changes), then
# upload the contents of this folder to the HF Space (or `git push` to it).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/../redactors"
dst="$here/redactors"

if [ ! -d "$src" ]; then
    echo "ERROR: canonical package not found at $src" >&2
    exit 1
fi

rm -rf "$dst"
cp -r "$src" "$dst"
find "$dst" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

echo "Synced engine -> $dst"
echo "Space bundle ready in: $here"
echo "Upload these to Hugging Face:  app.py  requirements.txt  README.md  redactors/"
