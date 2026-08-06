#!/usr/bin/env python3
"""Fetch the official USC catalogue archive list and print available years.

Stdlib only (runs on the system python3, before the app's venv exists).
Output: one line per catalogue, newest first, tab-separated:
    2026-2027<TAB>22<TAB>current
    2025-2026<TAB>21<TAB>archived
Exits non-zero (and prints nothing) if the list cannot be fetched, in which
case the launcher falls back to a typed-year dialog.
"""

import re
import ssl
import sys
import urllib.request

URL = "https://catalogue.usc.edu/misc/catalog_list.php?catoid=22"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

ANCHOR_RE = re.compile(
    r"catoid=(\d+)[^>]*>\s*USC\s+Catalog(?:ue)?\s+(\d{4})\s*[-–]\s*(\d{4})\s*</a>([^<]{0,100})",
    re.IGNORECASE,
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        # python.org installs often lack CA certs (SSLCertVerificationError
        # arrives wrapped in URLError). This page is public, read-only data,
        # so an unverified retry is an acceptable fallback.
        if not isinstance(getattr(e, "reason", None), ssl.SSLError):
            raise
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return r.read().decode("utf-8", "replace")


def main() -> int:
    try:
        html = fetch(URL)
    except Exception as e:
        print(f"fetch failed: {e}", file=sys.stderr)
        return 1
    entries = {}
    for catoid, y1, y2, tail in ANCHOR_RE.findall(html):
        year = f"{y1}-{y2}"
        archived = "archived" in tail.lower()
        if year not in entries:
            entries[year] = (catoid, archived)
        elif archived:  # any archived marker wins over a bare nav link
            entries[year] = (catoid, True)
    if not entries:
        print("no catalogue entries parsed", file=sys.stderr)
        return 1
    for year in sorted(entries, key=lambda y: int(y[:4]), reverse=True):
        catoid, archived = entries[year]
        print(f"{year}\t{catoid}\t{'archived' if archived else 'current'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
