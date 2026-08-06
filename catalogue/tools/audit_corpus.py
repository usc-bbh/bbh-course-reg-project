#!/usr/bin/env python3
"""Full-corpus audit of USC Catalogue Collector TXT output.

Inspects EVERY .txt file in one or more collection folders, cross-references
each file with its row in index.csv and its accepted attempt in fetch_log.csv,
computes content statistics and contamination signatures, and writes
scraper_output_audit.{csv,json,md}.

Usage:
    python3 audit_corpus.py OUT_DIR CORPUS_DIR [CORPUS_DIR ...]

A CORPUS_DIR is a collection folder containing programs/*.txt (plus optional
index.csv / fetch_log.csv / manifest.json).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- signatures
# Literal strings copied from the confirmed-defective 107 output plus generic
# failure fingerprints. Each entry: (key, regex, severity, human description)
SIGNATURES: list[tuple[str, str, str, str]] = [
    # --- exact fingerprints from the 107 Environmental Science defect ---
    ("skip_to_navigation", r"Skip to Navigation", "critical",
     "page-shell navigation link (whole-page capture)"),
    ("table_row_label", r"^Row \d+:", "critical",
     "'Row N:' table label from flattened page-layout table"),
    ("table_block_header", r"^TABLE:$", "high",
     "renderer TABLE block (page layout flattened as data table)"),
    ("usc_header_cell", r"\|\s*University of Southern California", "critical",
     "site header table cell captured as content"),
    ("responsive_markers", r"Begin Responsive|End Responsive", "critical",
     "acalog responsive-layout build markers (mid-render DOM)"),
    ("literal_script_tag", r"<\s*script[^>]*>|<\s*/\s*script\s*>", "critical",
     "literal <script> markup present as text"),
    ("literal_html_tag", r"<\s*(?:div|span|td|tr|table|ul|li|p|a|img|link|style|body|html|meta)\b[^>]*>",
     "critical", "literal HTML markup present as text"),
    ("js_filename", r"\b[\w/.-]+\.js\b", "high", "JavaScript filename in text"),
    ("css_filename", r"\b[\w/.-]+\.css\b", "high", "CSS filename in text"),
    ("html_entity", r"&(?:nbsp|amp|lt|gt|quot|#\d+);", "medium",
     "unresolved HTML entity"),
    # --- generic loading / error / bot-wall states ---
    ("loading_text", r"\b(?:Loading\.\.\.|Please wait|Just a moment)\b", "critical",
     "loading placeholder text"),
    ("js_error_text", r"(?:ReferenceError|TypeError:|undefined is not|Uncaught )", "critical",
     "JavaScript error text"),
    ("waf_text", r"(?:Request unsuccessful|Incapsula|verify you are human|Access Denied|"
                 r"Pardon our interruption|captcha)", "critical", "bot-wall / access-denied text"),
    ("cookie_consent", r"(?:accept all cookies|cookie policy|consent preferences)", "medium",
     "cookie/consent banner text"),
    ("nav_menu_run", r"Courses\s+Programs\s+School", "high",
     "navigation menu run-on (nav captured as content)"),
    ("noscript_banner", r"Javascript is currently not supported", "medium",
     "noscript banner captured"),
]

METADATA_KEYS = (
    "Program Name", "Credential", "School or Academic Unit", "Catalogue Year",
    "Catalogue Identifier", "Program Identifier", "Source URL", "Canonical URL",
    "Acquisition Mode", "Retrieved At", "Content SHA-256", "Extraction Status",
    "Breadcrumbs",
)
BODY_MARKER = "OFFICIAL CATALOGUE CONTENT"
COURSE_CODE_RE = re.compile(r"\b[A-Z]{2,5}\s\d{3}[A-Za-z]{0,3}\b")
UNITS_RE = re.compile(r"\bUnits:\s*\d", re.I)
HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.M)

# The app's own output validator is the single authority on whether a body is
# valid, so the audit and the scraper can never disagree. It is importable when
# this script is run with the app's venv python; otherwise the audit falls back
# to its own signature scan and says so in the report.
try:
    from usc_catalog_scraper.output_validation import validate_extracted_text
    VALIDATOR = "usc_catalog_scraper.output_validation.validate_extracted_text"
except Exception:  # pragma: no cover - depends on interpreter used
    validate_extracted_text = None  # type: ignore[assignment]
    VALIDATOR = "built-in fallback rules (app validator not importable)"


def parse_file(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", "replace")
    meta: dict[str, str] = {}
    body = text
    if BODY_MARKER in text:
        head, body = text.split(BODY_MARKER, 1)
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip() in METADATA_KEYS:
                    meta[k.strip()] = v.strip()
    body = body.strip("\n")
    return {"raw": raw, "text": text, "meta": meta, "body": body}


def norm_for_hash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def repeated_block_score(body: str) -> tuple[int, str]:
    """Longest sentence repeated N times inside the body (duplication signal)."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.strip()) > 80]
    if not sentences:
        return 1, ""
    counts = Counter(norm_for_hash(s) for s in sentences)
    key, n = counts.most_common(1)[0]
    return n, key[:120]


def audit_corpus(corpus: Path) -> list[dict]:
    programs = corpus / "programs"
    if not programs.is_dir():
        return []
    # index.csv: canonical expected title/url per file
    index_by_file: dict[str, dict] = {}
    idx = corpus / "index.csv"
    if idx.exists():
        for row in csv.DictReader(idx.open(encoding="utf-8")):
            # index.csv's column is `output_filename` — the earlier lookup list
            # omitted it, so index_by_file was always empty and the
            # title-mismatch check silently never ran.
            fn = (
                row.get("output_filename")
                or row.get("output_file")
                or row.get("filename")
                or row.get("file")
                or ""
            )
            if fn:
                index_by_file[Path(fn).name] = row
    # fetch_log.csv: accepted attempt per poid
    fetch_by_poid: dict[str, dict] = {}
    fl = corpus / "fetch_log.csv"
    if fl.exists():
        for row in csv.DictReader(fl.open(encoding="utf-8")):
            url = row.get("url", "")
            if "preview_program" not in url:
                continue
            m = re.search(r"poid=(\d+)", url)
            if not m:
                continue
            poid = m.group(1)
            # keep the accepted (result==ok) attempt; else the last attempt
            if row.get("result") == "ok" or poid not in fetch_by_poid:
                if row.get("result") == "ok" or fetch_by_poid.get(poid, {}).get("result") != "ok":
                    fetch_by_poid[poid] = row

    records: list[dict] = []
    for path in sorted(programs.glob("*.txt")):
        d = parse_file(path)
        meta, body, raw = d["meta"], d["body"], d["raw"]
        poid = (meta.get("Program Identifier", "").replace("poid=", "").strip())
        fetch = fetch_by_poid.get(poid, {})
        idx_row = index_by_file.get(path.name, {})

        chars = len(body)
        words = len(body.split())
        lines_ne = len([ln for ln in body.splitlines() if ln.strip()])
        hits: dict[str, int] = {}
        excerpts: list[str] = []
        for key, pattern, severity, desc in SIGNATURES:
            flags = re.M if pattern.startswith("^") else 0
            found = list(re.finditer(pattern, body, flags))
            if found:
                hits[key] = len(found)
                m0 = found[0]
                s = max(0, m0.start() - 60)
                excerpts.append(f"[{key}] …{body[s:m0.end() + 60].replace(chr(10), ' ⏎ ')}…")

        critical = [k for k, p, sev, dsc in SIGNATURES if k in hits and sev == "critical"]
        high = [k for k, p, sev, dsc in SIGNATURES if k in hits and sev == "high"]
        rep_n, rep_txt = repeated_block_score(body)
        course_codes = len(COURSE_CODE_RE.findall(body))
        units = len(UNITS_RE.findall(body))
        headings = len(HEADING_RE.findall(body))
        prog_name = meta.get("Program Name", "")
        # Does the body carry the program's own title as a heading?
        title_heading = bool(prog_name) and bool(
            re.search(r"^#{1,6}\s+" + re.escape(prog_name[:40]), body, re.M)
        )
        expected_title = (idx_row.get("program_name") or idx_row.get("title") or "").strip()
        title_mismatch = bool(expected_title and prog_name and
                              norm_for_hash(expected_title) != norm_for_hash(prog_name))

        failure_reasons: list[str] = []
        if validate_extracted_text is not None:
            # Authoritative verdict: identical rules to the scraper's write gate.
            ok, ev = validate_extracted_text(body, prog_name)
            failure_reasons.extend(ev.get("reasons", []))
            status = "PASS" if ok else "FAIL"
        else:
            ok = not (critical or rep_n >= 3 or chars < 200)
            if critical:
                failure_reasons.append("contamination:" + ",".join(critical))
            if rep_n >= 3:
                failure_reasons.append(f"duplicated_block_x{rep_n}")
            if chars < 200:
                failure_reasons.append("near_empty")
            if not title_heading and chars > 0:
                failure_reasons.append("no_title_heading_in_body")
            status = "PASS" if ok else "FAIL"
        # Advisory flags: never change a PASS into a FAIL, but surface for review.
        advisory: list[str] = []
        if title_mismatch:
            advisory.append("title_mismatch_vs_index")
        if fetch.get("http_status") == "202":
            advisory.append("accepted_on_http_202_waf_challenge")
        if chars < 400:
            advisory.append("very_short_body_check_source_page")
        failure_reasons.extend(advisory)
        if status == "PASS" and advisory:
            status = "REVIEW"

        records.append({
            "corpus": corpus.name,
            "file_name": path.name,
            "full_path": str(path),
            "source_url": meta.get("Source URL", "") or idx_row.get("source_url", ""),
            "program_name": prog_name,
            "expected_program_name": expected_title,
            "credential": meta.get("Credential", ""),
            "poid": poid,
            "acquisition_mode": meta.get("Acquisition Mode", ""),
            "retrieved_at": meta.get("Retrieved At", ""),
            "extraction_status_claimed": meta.get("Extraction Status", ""),
            "char_count": chars,
            "word_count": words,
            "nonempty_line_count": lines_ne,
            "byte_size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "normalized_body_sha256": hashlib.sha256(norm_for_hash(body).encode()).hexdigest(),
            "course_code_count": course_codes,
            "units_mentions": units,
            "markdown_heading_count": headings,
            "body_has_title_heading": title_heading,
            "title_mismatch": title_mismatch,
            "http_status_accepted": fetch.get("http_status", ""),
            "runtime_seconds": fetch.get("elapsed_seconds", ""),
            "fetch_attempts_mode": fetch.get("acquisition_mode", ""),
            "dom_bytes_at_capture": fetch.get("content_length", ""),
            "has_html_like_tags": bool({"literal_script_tag", "literal_html_tag"} & set(hits)),
            "signature_hits": ";".join(f"{k}={v}" for k, v in sorted(hits.items())),
            "critical_signatures": ",".join(critical),
            "high_signatures": ",".join(high),
            "max_repeated_sentence_count": rep_n,
            "repeated_sentence_excerpt": rep_txt,
            "validation_status": status,
            "failure_reasons": ";".join(failure_reasons),
            "suspicious_excerpts": " || ".join(excerpts[:4]),
        })
    return records


def stats_block(records: list[dict]) -> dict:
    counts = [r["char_count"] for r in records]
    counts_nz = sorted(c for c in counts if c > 0)
    out: dict = {"file_count": len(records)}
    if not counts_nz:
        return out
    mean = statistics.mean(counts_nz)
    median = statistics.median(counts_nz)
    sd = statistics.pstdev(counts_nz) if len(counts_nz) > 1 else 0.0
    q1, q3 = (statistics.quantiles(counts_nz, n=4)[0], statistics.quantiles(counts_nz, n=4)[2]) \
        if len(counts_nz) >= 4 else (counts_nz[0], counts_nz[-1])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    by_chars = sorted(records, key=lambda r: r["char_count"])
    nz = [r for r in by_chars if r["char_count"] > 0]
    out.update({
        "min_chars": counts_nz[0], "max_chars": counts_nz[-1],
        "mean_chars": round(mean, 1), "median_chars": median,
        "stdev_chars": round(sd, 1), "q1": q1, "q3": q3, "iqr": iqr,
        "iqr_lower_fence": round(lo, 1), "iqr_upper_fence": round(hi, 1),
        "largest_file": {"name": nz[-1]["file_name"], "chars": nz[-1]["char_count"]} if nz else {},
        "five_smallest_nonzero": [{"name": r["file_name"], "chars": r["char_count"],
                                   "status": r["validation_status"]} for r in nz[:5]],
        "five_largest": [{"name": r["file_name"], "chars": r["char_count"],
                          "status": r["validation_status"]} for r in nz[-5:][::-1]],
        "below_iqr_lower_fence": [r["file_name"] for r in nz if r["char_count"] < lo],
        "above_iqr_upper_fence": [r["file_name"] for r in nz if r["char_count"] > hi],
        "extreme_z_scores": [
            {"name": r["file_name"], "z": round((r["char_count"] - mean) / sd, 2)}
            for r in nz if sd and abs((r["char_count"] - mean) / sd) >= 3
        ],
    })
    return out


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for c in sys.argv[2:]:
        got = audit_corpus(Path(c))
        print(f"audited {len(got):4d} files in {c}")
        records.extend(got)
    if not records:
        print("no files audited")
        return 1

    # duplicate / near-duplicate grouping on normalized body
    groups: dict[str, list[str]] = defaultdict(list)
    for r in records:
        groups[r["normalized_body_sha256"]].append(r["file_name"])
    for r in records:
        g = groups[r["normalized_body_sha256"]]
        r["duplicate_group_size"] = len(g)
        r["duplicate_group_members"] = ";".join(sorted(g)) if len(g) > 1 else ""
        if len(g) > 1 and "exact_duplicate_body" not in r["failure_reasons"]:
            r["failure_reasons"] = ";".join(
                filter(None, [r["failure_reasons"], "exact_duplicate_body"]))
            if r["validation_status"] == "PASS":
                r["validation_status"] = "REVIEW"

    fails = [r for r in records if r["validation_status"] == "FAIL"]
    reviews = [r for r in records if r["validation_status"] == "REVIEW"]
    for r in records:
        r["manual_review_priority"] = (
            1 if r["validation_status"] == "FAIL"
            else 2 if r["critical_signatures"] or r["high_signatures"]
            else 3 if r["validation_status"] == "REVIEW" else 9)

    cols = list(records[0].keys())
    with (out_dir / "scraper_output_audit.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(records)

    overall = stats_block(records)
    per_corpus = {c: stats_block([r for r in records if r["corpus"] == c])
                  for c in sorted({r["corpus"] for r in records})}
    sig_totals = Counter()
    for r in records:
        for part in filter(None, r["signature_hits"].split(";")):
            sig_totals[part.split("=")[0]] += 1
    payload = {
        "generated_for": "USC Catalogue Collector incident audit",
        "validator": VALIDATOR,
        "corpora": sys.argv[2:],
        "totals": {
            "files": len(records),
            "PASS": len(records) - len(fails) - len(reviews),
            "REVIEW": len(reviews),
            "FAIL": len(fails),
        },
        "signature_file_counts": dict(sig_totals.most_common()),
        "statistics_overall": overall,
        "statistics_per_corpus": per_corpus,
        "failed_files": [
            {k: r[k] for k in ("corpus", "file_name", "program_name", "source_url", "char_count",
                               "http_status_accepted", "runtime_seconds", "critical_signatures",
                               "max_repeated_sentence_count", "failure_reasons",
                               "suspicious_excerpts")}
            for r in sorted(fails, key=lambda x: x["file_name"])],
        "review_files": [
            {k: r[k] for k in ("corpus", "file_name", "program_name", "char_count",
                               "http_status_accepted", "failure_reasons")}
            for r in sorted(reviews, key=lambda x: x["file_name"])],
        "records": records,
    }
    (out_dir / "scraper_output_audit.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def md_table(rows: list[list[str]], head: list[str]) -> str:
        out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
        out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
        return "\n".join(out)

    md = [f"# Scraper output audit — {len(records)} TXT files", "",
          f"- PASS **{payload['totals']['PASS']}** · REVIEW **{len(reviews)}** · FAIL **{len(fails)}**",
          "", "## Corpus statistics", ""]
    md.append(md_table(
        [[c, s.get("file_count"), s.get("min_chars"), s.get("max_chars"), s.get("mean_chars"),
          s.get("median_chars"), s.get("stdev_chars"), s.get("q1"), s.get("q3"), s.get("iqr")]
         for c, s in per_corpus.items()],
        ["corpus", "files", "min", "max", "mean", "median", "stdev", "Q1", "Q3", "IQR"]))
    md += ["", "## Contamination signatures (files affected)", ""]
    md.append(md_table([[k, v] for k, v in sig_totals.most_common()], ["signature", "files"]))
    md += ["", "## FAIL files", ""]
    if fails:
        md.append(md_table(
            [[r["file_name"], r["char_count"], r["http_status_accepted"],
              r["critical_signatures"] or "-", r["max_repeated_sentence_count"]]
             for r in sorted(fails, key=lambda x: x["file_name"])],
            ["file", "chars", "http", "critical signatures", "max repeat"]))
    else:
        md.append("_none_")
    md += ["", "## Five smallest non-empty / five largest (overall)", ""]
    md.append("Smallest: " + ", ".join(
        f"{r['name']} ({r['chars']}, {r['status']})" for r in overall["five_smallest_nonzero"]))
    md.append("")
    md.append("Largest: " + ", ".join(
        f"{r['name']} ({r['chars']}, {r['status']})" for r in overall["five_largest"]))
    md += ["", "## Statistical outliers (overall)", "",
           f"- IQR fences: lower {overall['iqr_lower_fence']}, upper {overall['iqr_upper_fence']}",
           f"- Below lower fence ({len(overall['below_iqr_lower_fence'])}): "
           + (", ".join(overall["below_iqr_lower_fence"][:25]) or "none"),
           f"- Above upper fence ({len(overall['above_iqr_upper_fence'])}): "
           + (", ".join(overall["above_iqr_upper_fence"][:25]) or "none"),
           f"- |z| >= 3 ({len(overall['extreme_z_scores'])}): "
           + (", ".join(f"{e['name']} z={e['z']}" for e in overall["extreme_z_scores"][:25]) or "none")]
    (out_dir / "scraper_output_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"\nTOTals: PASS={payload['totals']['PASS']} REVIEW={len(reviews)} FAIL={len(fails)}")
    for r in sorted(fails, key=lambda x: x["file_name"]):
        print(f"  FAIL {r['file_name']:<60} chars={r['char_count']:<7} http={r['http_status_accepted']} "
              f"sigs={r['critical_signatures']}")
    print(f"\nwrote {out_dir}/scraper_output_audit.{{csv,json,md}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
