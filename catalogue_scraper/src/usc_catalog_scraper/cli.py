"""Command line interface: inspect / smoke / run / audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from usc_catalog_scraper import __version__, config
from usc_catalog_scraper.logging_config import setup_logging

app = typer.Typer(
    add_completion=False,
    help=(
        "USC Catalogue undergraduate-program collector. "
        "Collects one plain-text file per standalone undergraduate degree "
        "program from the latest USC Catalogue, with strict section-boundary "
        "discovery, layered acquisition, and safe resume."
    ),
)
console = Console()


def _build_config(
    start_url: str,
    output_dir: Path | None,
    latest: bool,
    headed: bool,
    headless: bool,
    resume: bool,
    overwrite: bool,
    max_programs: int | None,
    delay_min: float,
    delay_max: float,
    max_retries: int,
    save_raw_html: bool,
    save_rendered_html: bool,
    save_failure_screenshots: bool,
    browser_profile_dir: Path | None,
    catalogue_year: str | None,
    strict: bool,
    verbose: bool,
    boundary_heading: str,
    workdir: Path | None,
    chromium_sandbox: bool = True,
) -> config.ScraperConfig:
    cfg = config.ScraperConfig(
        start_url=start_url,
        output_dir=output_dir,
        latest_resolution=latest,
        headed=headed,
        headless=headless and not headed,
        resume=resume,
        overwrite=overwrite,
        max_programs=max_programs,
        delay_min=delay_min,
        delay_max=delay_max,
        max_retries=max_retries,
        save_raw_html=save_raw_html,
        save_rendered_html=save_rendered_html,
        save_failure_screenshots=save_failure_screenshots,
        browser_profile_dir=browser_profile_dir,
        catalogue_year=catalogue_year,
        strict=strict,
        verbose=verbose,
        boundary_heading=boundary_heading or config.TARGET_SECTION_HEADING,
        workdir=workdir or Path.cwd(),
        chromium_sandbox=chromium_sandbox,
    )
    return cfg


# Shared option declarations (typer requires repetition per command).
_START_URL = typer.Option(
    config.DEFAULT_START_URL, "--start-url", help="Programs page URL to start from."
)
_OUTPUT_DIR = typer.Option(
    None,
    "--output-dir",
    help="Output folder (default: usc_undergraduate_catalogue_<year> in the working folder).",
)
_LATEST = typer.Option(
    True,
    "--latest/--no-latest-resolution",
    help="Resolve the newest current catalogue from the official archive list (or force the supplied URL).",
)
_HEADED = typer.Option(
    False,
    "--headed",
    help="Run the browser visibly (required the first time if a verification page appears).",
)
_HEADLESS = typer.Option(
    True,
    "--headless/--no-headless",
    help="Run the browser headless once a verified session exists.",
)
_RESUME = typer.Option(
    True, "--resume/--no-resume", help="Skip programs already completed with matching hashes."
)
_OVERWRITE = typer.Option(
    False, "--overwrite", help="Re-extract everything, rewriting output files."
)
_MAX_PROGRAMS = typer.Option(None, "--max-programs", help="Process at most N programs this run.")
_DELAY_MIN = typer.Option(3.5, "--delay-min", help="Minimum seconds between requests.")
_DELAY_MAX = typer.Option(7.5, "--delay-max", help="Maximum seconds between requests.")
_MAX_RETRIES = typer.Option(4, "--max-retries", help="Transport retry attempts per request.")
_SAVE_RAW = typer.Option(
    False,
    "--save-raw-html/--no-save-raw-html",
    help="Keep raw HTTP HTML in audit_evidence/raw_pages.",
)
_SAVE_RENDERED = typer.Option(
    False,
    "--save-rendered-html/--no-save-rendered-html",
    help="Keep rendered DOM snapshots in audit_evidence/rendered_pages.",
)
_SAVE_SCREENSHOTS = typer.Option(
    True,
    "--save-failure-screenshots/--no-save-failure-screenshots",
    help="Screenshot failed/ambiguous browser pages.",
)
_PROFILE_DIR = typer.Option(
    None,
    "--browser-profile-dir",
    help="Persistent browser profile folder (default: <output>/state/browser_profile).",
)
_CATALOGUE_YEAR = typer.Option(
    None, "--catalogue-year", help="Override detected catalogue year (e.g. 2026-2027)."
)
_STRICT = typer.Option(
    True,
    "--strict/--no-strict",
    help="Refuse to scrape when the section boundary cannot be proven.",
)
_VERBOSE = typer.Option(False, "--verbose", "-v", help="Debug logging.")
_BOUNDARY_HEADING = typer.Option(
    config.TARGET_SECTION_HEADING,
    "--boundary-heading",
    help='Exact section heading to bound discovery (default "Undergraduate Programs").',
)
_WORKDIR = typer.Option(
    None, "--workdir", help="Project working folder (default: current directory)."
)
_MINORS = typer.Option(
    False,
    "--minors/--bachelors",
    help="Collect minors instead of standalone bachelor's degree programs.",
)
_ALL_UNDERGRAD = typer.Option(
    False,
    "--all-undergrad",
    help="Collect bachelor's degree programs AND minors (graduate programs and certificates stay excluded).",
)
_CHROMIUM_SANDBOX = typer.Option(
    True,
    "--chromium-sandbox/--no-chromium-sandbox",
    help="Disable only inside containers without user namespaces (CI).",
)


@app.command()
def inspect(
    start_url: str = _START_URL,
    latest: bool = _LATEST,
    headed: bool = _HEADED,
    headless: bool = _HEADLESS,
    delay_min: float = _DELAY_MIN,
    delay_max: float = _DELAY_MAX,
    max_retries: int = _MAX_RETRIES,
    browser_profile_dir: Path | None = _PROFILE_DIR,
    boundary_heading: str = _BOUNDARY_HEADING,
    verbose: bool = _VERBOSE,
    workdir: Path | None = _WORKDIR,
    no_browser: bool = typer.Option(False, "--no-browser", help="Probe with direct HTTP only."),
) -> None:
    """Probe the live site: acquisition behavior, resolution, boundary evidence."""
    from usc_catalog_scraper.acquisition import AcquisitionOrchestrator
    from usc_catalog_scraper.boundary import BoundaryNotProvableError
    from usc_catalog_scraper.catalogue_resolver import resolve_latest
    from usc_catalog_scraper.discovery import discover_program_links
    from usc_catalog_scraper.models import PageKind
    from usc_catalog_scraper.state import StateDB

    cfg = _build_config(
        start_url,
        None,
        latest,
        headed,
        headless,
        True,
        False,
        None,
        delay_min,
        delay_max,
        max_retries,
        False,
        False,
        True,
        browser_profile_dir,
        None,
        True,
        verbose,
        boundary_heading,
        workdir,
    )
    if no_browser:
        cfg.allow_browser = False
    setup_logging(cfg.verbose)
    work = cfg.workdir / "inspect_evidence"
    work.mkdir(parents=True, exist_ok=True)
    db = StateDB(work / "inspect.sqlite3")
    orch = AcquisitionOrchestrator(
        cfg, db, state_dir=work, screenshots_dir=work / "screenshots", headed=cfg.headed
    )
    report: dict = {"start_url": start_url}
    try:
        console.rule("Layer 1: direct HTTP on supplied URL")
        from usc_catalog_scraper.acquisition import HumanVerificationRequired

        try:
            direct = orch.http.fetch(start_url, PageKind.PROGRAMS_INDEX)
            report["direct_http"] = {
                "mode": direct.mode.value,
                "status": direct.http_status,
                "bytes": len(direct.html or ""),
                "challenge": direct.challenge_detected,
                "challenge_evidence": direct.challenge_evidence,
                "semantic": direct.semantic_evidence,
            }
            console.print(report["direct_http"])
        except Exception as e:
            report["direct_http"] = {"error": f"{type(e).__name__}: {e}"}
            console.print(report["direct_http"])

        console.rule("Catalogue resolution")
        try:
            resolution = resolve_latest(orch, cfg)
            report["resolution"] = {
                "resolved_url": resolution.resolved_url,
                "catalogue": vars(resolution.catalogue),
                "method": resolution.method,
                "verified": resolution.verified,
                "notes": resolution.notes,
            }
            console.print(report["resolution"])
        except HumanVerificationRequired as e:
            report["resolution"] = {"human_verification_required": e.instructions}
            console.print(report["resolution"])
            resolution = None

        console.rule("Programs index acquisition + boundary")
        target_url = (
            report.get("resolution", {}).get("resolved_url") or start_url
            if isinstance(report.get("resolution"), dict)
            else start_url
        )
        try:
            index_result = orch.acquire(target_url, PageKind.PROGRAMS_INDEX, label="inspect_index")
            report["index_acquisition"] = {
                "mode": index_result.mode.value,
                "status": index_result.http_status,
                "final_url": index_result.final_url,
                "semantic": index_result.semantic_evidence,
                "challenge": index_result.challenge_detected,
            }
            console.print(report["index_acquisition"])
            if index_result.html:
                (work / "index_snapshot.html").write_text(index_result.html, encoding="utf-8")
            if index_result.ok:
                try:
                    links, boundary, dups, _ = discover_program_links(
                        index_result.html, index_result.final_url or target_url, cfg, strict=True
                    )
                    report["boundary"] = boundary.to_dict()
                    report["boundary"]["duplicates"] = dups
                    report["sample_links"] = [
                        {"seq": lk.sequence, "title": lk.title, "url": lk.canonical_url}
                        for lk in links[:8]
                    ]
                    console.print(
                        f"[green]Boundary proven[/green]: {len(links)} links; "
                        f"heading={boundary.heading.text if boundary.heading else None!r}; "
                        f"terminated by {boundary.terminating_heading.text if boundary.terminating_heading else boundary.terminated_by!r}"
                    )
                except BoundaryNotProvableError as e:
                    report["boundary"] = {"error": str(e), "headings_seen": e.headings_seen}
                    console.print(f"[red]Boundary NOT provable[/red]: {e}")
        except HumanVerificationRequired as e:
            report["index_acquisition"] = {"human_verification_required": e.instructions}
            console.print(f"[yellow]{e.instructions}[/yellow]")
    finally:
        orch.close()
        db.close()
        out = work / "inspect_report.json"
        out.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        console.print(f"\nInspection evidence written to {out}")


def _execute(cfg: config.ScraperConfig, smoke: bool) -> None:
    from usc_catalog_scraper.pipeline import run_pipeline

    outcome = run_pipeline(cfg, smoke=smoke)
    console.rule("Result")
    console.print(
        {
            "run_id": outcome.run_id,
            "output_root": str(outcome.output_root) if outcome.output_root else None,
            "resolved_url": outcome.resolved_url,
            "catalogue_year": outcome.catalogue_year,
            "included": outcome.included,
            "excluded": outcome.excluded,
            "manual_review": outcome.manual_review,
            "duplicates": outcome.duplicates,
            "processed_this_run": outcome.processed,
            "succeeded_this_run": outcome.succeeded,
            "failed_this_run": outcome.failed,
            "stopped_reason": outcome.stopped_reason or "completed",
        }
    )
    if outcome.stopped_reason:
        console.print(f"[yellow]STOPPED EARLY:[/yellow] {outcome.stopped_reason}")
        raise typer.Exit(code=2)
    if outcome.problems:
        console.print(f"[red]Output verification problems:[/red] {outcome.problems[:5]}")
        raise typer.Exit(code=3)


@app.command()
def smoke(
    start_url: str = _START_URL,
    output_dir: Path | None = _OUTPUT_DIR,
    latest: bool = _LATEST,
    headed: bool = _HEADED,
    headless: bool = _HEADLESS,
    resume: bool = _RESUME,
    overwrite: bool = _OVERWRITE,
    max_programs: int = typer.Option(
        4, "--max-programs", help="Programs to process in the smoke run."
    ),
    delay_min: float = _DELAY_MIN,
    delay_max: float = _DELAY_MAX,
    max_retries: int = _MAX_RETRIES,
    save_raw_html: bool = typer.Option(
        True, "--save-raw-html/--no-save-raw-html", help="Smoke runs keep raw HTML by default."
    ),
    save_rendered_html: bool = typer.Option(
        True,
        "--save-rendered-html/--no-save-rendered-html",
        help="Smoke runs keep rendered DOM by default.",
    ),
    save_failure_screenshots: bool = _SAVE_SCREENSHOTS,
    browser_profile_dir: Path | None = _PROFILE_DIR,
    catalogue_year: str | None = _CATALOGUE_YEAR,
    strict: bool = _STRICT,
    verbose: bool = _VERBOSE,
    boundary_heading: str = _BOUNDARY_HEADING,
    workdir: Path | None = _WORKDIR,
    chromium_sandbox: bool = _CHROMIUM_SANDBOX,
    minors: bool = _MINORS,
    all_undergrad: bool = _ALL_UNDERGRAD,
) -> None:
    """Live smoke test: process a handful of programs end to end with evidence retained."""
    cfg = _build_config(
        start_url,
        output_dir,
        latest,
        headed,
        headless,
        resume,
        overwrite,
        max_programs,
        delay_min,
        delay_max,
        max_retries,
        save_raw_html,
        save_rendered_html,
        save_failure_screenshots,
        browser_profile_dir,
        catalogue_year,
        strict,
        verbose,
        boundary_heading,
        workdir,
        chromium_sandbox,
    )
    cfg.collect_minors = minors
    cfg.collect_all_undergrad = all_undergrad
    _execute(cfg, smoke=True)


@app.command()
def run(
    start_url: str = _START_URL,
    output_dir: Path | None = _OUTPUT_DIR,
    latest: bool = _LATEST,
    headed: bool = _HEADED,
    headless: bool = _HEADLESS,
    resume: bool = _RESUME,
    overwrite: bool = _OVERWRITE,
    max_programs: int | None = _MAX_PROGRAMS,
    delay_min: float = _DELAY_MIN,
    delay_max: float = _DELAY_MAX,
    max_retries: int = _MAX_RETRIES,
    save_raw_html: bool = _SAVE_RAW,
    save_rendered_html: bool = _SAVE_RENDERED,
    save_failure_screenshots: bool = _SAVE_SCREENSHOTS,
    browser_profile_dir: Path | None = _PROFILE_DIR,
    catalogue_year: str | None = _CATALOGUE_YEAR,
    strict: bool = _STRICT,
    verbose: bool = _VERBOSE,
    boundary_heading: str = _BOUNDARY_HEADING,
    workdir: Path | None = _WORKDIR,
    chromium_sandbox: bool = _CHROMIUM_SANDBOX,
    minors: bool = _MINORS,
    all_undergrad: bool = _ALL_UNDERGRAD,
) -> None:
    """Full extraction of every standalone undergraduate degree program (or every minor)."""
    cfg = _build_config(
        start_url,
        output_dir,
        latest,
        headed,
        headless,
        resume,
        overwrite,
        max_programs,
        delay_min,
        delay_max,
        max_retries,
        save_raw_html,
        save_rendered_html,
        save_failure_screenshots,
        browser_profile_dir,
        catalogue_year,
        strict,
        verbose,
        boundary_heading,
        workdir,
        chromium_sandbox,
    )
    cfg.collect_minors = minors
    cfg.collect_all_undergrad = all_undergrad
    _execute(cfg, smoke=False)


@app.command()
def audit(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Collection folder to audit (default: newest usc_undergraduate_catalogue_* in the working folder).",
    ),
    workdir: Path | None = _WORKDIR,
    verbose: bool = _VERBOSE,
) -> None:
    """Verify hashes, counts, and index consistency; write AUDIT_REPORT.md."""
    from usc_catalog_scraper.audit import run_audit, write_audit_report

    cfg = config.ScraperConfig(workdir=workdir or Path.cwd(), verbose=verbose)
    setup_logging(verbose)
    root = output_dir
    if root is None:
        candidates = sorted((cfg.workdir).glob("usc_*_catalogue_*"))
        if not candidates:
            console.print("[red]No collection folder found to audit.[/red]")
            raise typer.Exit(code=1)
        root = candidates[-1]
    passed, report = run_audit(root, cfg)
    path = write_audit_report(cfg.workdir, root, report, cfg)
    console.print(json.dumps({"passed": passed, "checks": report.get("checks", [])}, indent=2))
    console.print(f"Audit report: {path}")
    raise typer.Exit(code=0 if passed else 4)


@app.command()
def version() -> None:
    """Print version."""
    console.print(f"usc-catalog-scraper {__version__}")


def main() -> None:  # entry point
    try:
        app(standalone_mode=True)
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Interrupted. State is saved; rerun with --resume to continue.[/yellow]"
        )
        sys.exit(130)


if __name__ == "__main__":
    main()
