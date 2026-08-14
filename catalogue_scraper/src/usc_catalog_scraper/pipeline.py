"""End-to-end pipeline: resolve -> acquire index -> boundary -> discover ->
classify -> extract each program -> render -> write -> index. Resume-safe."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from usc_catalog_scraper import config
from usc_catalog_scraper.acquisition import (
    AcquisitionOrchestrator,
    HumanVerificationRequired,
)
from usc_catalog_scraper.boundary import BoundaryNotProvableError
from usc_catalog_scraper.catalogue_resolver import params_of, resolve_latest
from usc_catalog_scraper.classification import classify_title, reconcile_with_page_evidence
from usc_catalog_scraper.discovery import discover_program_links
from usc_catalog_scraper.extraction import (
    ContentRegionNotFound,
    capture_breadcrumbs,
    clean_content,
    extract_metadata,
    select_main_container,
)
from usc_catalog_scraper.logging_config import get_logger, setup_logging
from usc_catalog_scraper.models import (
    AcquisitionMode,
    Classification,
    ExtractionStatus,
    PageKind,
    utcnow_iso,
)
from usc_catalog_scraper.output import (
    atomic_write_text,
    build_filename,
    compose_program_file,
    regenerate_all,
    write_output_readme,
)
from usc_catalog_scraper.output_validation import validate_extracted_text
from usc_catalog_scraper.state import StateDB, sha256_file, sha256_text
from usc_catalog_scraper.text_renderer import render_text

log = get_logger("pipeline")


@dataclass
class PipelineOutcome:
    run_id: str
    output_root: Path | None
    resolved_url: str = ""
    catalogue_year: str = ""
    included: int = 0
    excluded: int = 0
    manual_review: int = 0
    duplicates: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    stopped_reason: str = ""
    boundary: dict | None = None
    problems: list[str] | None = None


def _write_boundary_evidence(layout: config.OutputLayout, payload: dict) -> None:
    atomic_write_text(
        layout.audit_evidence / "index_boundary.json",
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )


def _bootstrap_orchestrator(cfg: config.ScraperConfig, tmp_state: Path, headed: bool):
    tmp_state.mkdir(parents=True, exist_ok=True)
    boot_db = StateDB(tmp_state / "bootstrap.sqlite3")
    orch = AcquisitionOrchestrator(
        cfg,
        boot_db,
        state_dir=tmp_state,
        screenshots_dir=tmp_state / "screenshots",
        headed=headed,
    )
    return boot_db, orch


def _merge_bootstrap(boot_db: StateDB, db: StateDB) -> None:
    for table in ("fetch_log", "errors", "resolution"):
        rows = boot_db.conn.execute(f"SELECT * FROM {table}").fetchall()
        for row in rows:
            keys = [k for k in row.keys() if k != "id"]  # noqa: SIM118 - sqlite3.Row has no __iter__ over keys
            placeholders = ",".join("?" for _ in keys)
            db.conn.execute(
                f"INSERT INTO {table}({','.join(keys)}) VALUES ({placeholders})",
                [row[k] for k in keys],
            )
    db.conn.commit()


def run_pipeline(
    cfg: config.ScraperConfig,
    smoke: bool = False,
) -> PipelineOutcome:
    run_id = f"{'smoke' if smoke else 'run'}-{utcnow_iso().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:6]}"
    setup_logging(cfg.verbose)
    workdir = cfg.workdir
    workdir.mkdir(parents=True, exist_ok=True)

    headed = cfg.headed or not cfg.headless

    # ---------------------------------------------------------- resolution
    boot_state = workdir / ".bootstrap_state"
    boot_db, boot_orch = _bootstrap_orchestrator(cfg, boot_state, headed)
    outcome = PipelineOutcome(run_id=run_id, output_root=None)
    try:
        resolution = resolve_latest(boot_orch, cfg)
    except HumanVerificationRequired as e:
        boot_orch.close()
        boot_db.close()
        outcome.stopped_reason = f"human verification required during resolution: {e.instructions}"
        log.error(outcome.stopped_reason)
        return outcome
    finally:
        # Browser stays open through the run; only close bootstrap HTTP later.
        pass

    catalogue = resolution.catalogue
    year = cfg.catalogue_year or catalogue.year or ""
    if not year:
        # Try to read the year from the programs page itself later; use a
        # placeholder folder that is renamed only in documentation, never data.
        year = "unknown_year"
    if cfg.collect_all_undergrad:
        prefix = "usc_undergrad_complete_catalogue"
    elif cfg.collect_minors:
        prefix = "usc_minors_catalogue"
    else:
        prefix = "usc_undergraduate_catalogue"
    root = cfg.output_dir or config.output_root_for_year(workdir, year, prefix)
    layout = config.OutputLayout(root=root)
    layout.create()
    outcome.output_root = root
    setup_logging(cfg.verbose, log_file=root / "run_log.txt")
    log.info("Run %s starting; output root: %s", run_id, root)
    for note in resolution.notes:
        log.info("resolution: %s", note)

    db = StateDB(layout.db_path)
    db.start_run(run_id, {k: str(v) for k, v in vars(cfg).items()})
    _merge_bootstrap(boot_db, db)
    boot_db.close()

    db.save_resolution(
        run_id,
        supplied_url=resolution.supplied_url,
        resolved_url=resolution.resolved_url,
        catalogue_title=catalogue.title,
        catalogue_year=year if year != "unknown_year" else "",
        catoid=catalogue.catoid,
        navoid=catalogue.navoid,
        method=resolution.method,
        verified=resolution.verified,
        notes=resolution.notes,
    )
    outcome.resolved_url = resolution.resolved_url
    outcome.catalogue_year = year

    # Real orchestrator writes to the real DB/layout from here on.
    orch = AcquisitionOrchestrator(
        cfg,
        db,
        state_dir=layout.state_dir,
        screenshots_dir=layout.screenshots,
        raw_dir=layout.raw_pages,
        rendered_dir=layout.rendered_pages,
        headed=headed,
    )
    # Reuse the bootstrap browser session if it was started.
    if boot_orch._browser is not None:
        orch._browser = boot_orch._browser
        orch._browser.screenshots_dir = layout.screenshots
    boot_orch.http.close()

    try:
        return _run_core(cfg, db, orch, layout, resolution, run_id, outcome, smoke)
    finally:
        try:
            db.set_kv(
                "playwright_browser_version",
                orch._browser.browser_version() if orch._browser else "browser layer not used",
            )
        except Exception:
            pass
        regenerate_all(db, root, run_id, cfg)
        write_output_readme(root, year)
        db.complete_run(run_id, notes=outcome.stopped_reason or "ok")
        orch.close()
        db.close()


def _run_core(
    cfg: config.ScraperConfig,
    db: StateDB,
    orch: AcquisitionOrchestrator,
    layout: config.OutputLayout,
    resolution,
    run_id: str,
    outcome: PipelineOutcome,
    smoke: bool,
) -> PipelineOutcome:
    root = layout.root

    # ------------------------------------------------------------ index page
    try:
        index_result = orch.acquire(
            resolution.resolved_url, PageKind.PROGRAMS_INDEX, label="programs_index"
        )
    except HumanVerificationRequired as e:
        outcome.stopped_reason = str(e.instructions)
        log.error("STOPPED: %s", e.instructions)
        return outcome
    if not index_result.ok:
        outcome.stopped_reason = (
            f"programs index page could not be acquired: mode={index_result.mode.value}, "
            f"error={index_result.error or index_result.semantic_evidence}"
        )
        db.log_error(
            stage="index_acquisition",
            source_url=resolution.resolved_url,
            error_type=index_result.mode.value,
            error_message=str(index_result.error or index_result.semantic_evidence)[:1500],
            acquisition_mode=index_result.mode.value,
            retryable=True,
        )
        log.error("STOPPED: %s", outcome.stopped_reason)
        return outcome

    # Fill the catalogue year from live page evidence when still unknown.
    year = outcome.catalogue_year
    if year in ("", "unknown_year"):
        m = re.search(r"USC\s+Catalogue\s+(\d{4}-\d{4})", index_result.html)
        if m:
            year = m.group(1)
            outcome.catalogue_year = year

    # -------------------------------------------------------------- boundary
    try:
        links, boundary, duplicates, _section = discover_program_links(
            index_result.html,
            index_result.final_url or resolution.resolved_url,
            cfg,
            strict=cfg.strict,
        )
    except BoundaryNotProvableError as e:
        outcome.stopped_reason = (
            f"BOUNDARY NOT PROVABLE: {e}. Strict mode refuses to scrape. "
            "Run 'inspect' to see candidate headings; if the section uses a "
            'different title, rerun with --boundary-heading "<exact title>".'
        )
        db.save_boundary(run_id, {"error": str(e), "headings_seen": e.headings_seen})
        atomic_write_text(
            layout.audit_evidence / "index_boundary.json",
            json.dumps({"error": str(e), "headings_seen": e.headings_seen}, indent=2) + "\n",
        )
        log.error("STOPPED: %s", outcome.stopped_reason)
        return outcome

    outcome.duplicates = duplicates
    db.set_kv("duplicate_count", duplicates)
    boundary_payload = boundary.to_dict()
    boundary_payload["acquisition_mode"] = index_result.mode.value
    boundary_payload["index_url"] = index_result.final_url
    db.save_boundary(run_id, boundary_payload)
    _write_boundary_evidence(layout, boundary_payload)
    atomic_write_text(layout.audit_evidence / "index_boundary.html", index_result.html)
    outcome.boundary = boundary_payload
    log.info(
        "Boundary proven: heading=%r (level %s, %s) terminated by %r; %d links, %d duplicates",
        boundary.heading.text if boundary.heading else None,
        boundary.heading.level if boundary.heading else None,
        boundary.heading.source if boundary.heading else None,
        boundary.terminating_heading.text
        if boundary.terminating_heading
        else boundary.terminated_by,
        len(links),
        duplicates,
    )

    # ------------------------------------------------- link upsert + classify
    existing_max = db.conn.execute("SELECT COALESCE(MAX(seq),0) m FROM links").fetchone()["m"]
    next_seq = int(existing_max)
    for link in links:
        row = db.link(link.catoid, link.poid)
        if row is None:
            next_seq += 1
            link.sequence = next_seq
        else:
            link.sequence = int(row["seq"])
        db.upsert_link(link, run_id)
        result = classify_title(link.title, link.section_heading, cfg=cfg)
        db.record_classification(link.catoid, link.poid, result)
        if result.classification is Classification.INCLUDED:
            db.ensure_program_row(link.catoid, link.poid)

    counts = db.counts()
    outcome.included = counts.get(Classification.INCLUDED.value, 0)
    outcome.excluded = sum(v for k, v in counts.items() if k.startswith("excluded_"))
    outcome.manual_review = counts.get(Classification.MANUAL_REVIEW.value, 0)
    # Boundary evidence: first/last INCLUDED links; evidence file kept in
    # sync with the authoritative database record.
    included_rows = db.links_by_classification(Classification.INCLUDED)
    if included_rows:
        boundary_payload["first_included_title"] = included_rows[0]["title"]
        boundary_payload["last_included_title"] = included_rows[-1]["title"]
        boundary_payload["links_rejected_after_classification"] = (
            outcome.excluded + outcome.manual_review
        )
        db.save_boundary(run_id, boundary_payload)
        _write_boundary_evidence(layout, boundary_payload)
    log.info(
        "Classification: %d included, %d excluded, %d manual review",
        outcome.included,
        outcome.excluded,
        outcome.manual_review,
    )

    # ------------------------------------------------------------ extraction
    if cfg.overwrite:
        with db.tx() as c:
            c.execute("UPDATE programs SET extraction_status='pending'")
    pending = db.needs_extraction(layout.programs)
    if cfg.max_programs is not None:
        pending = pending[: cfg.max_programs]
    log.info("Programs to process this run: %d", len(pending))

    taken = db.existing_filenames()
    for row in pending:
        catoid, poid = str(row["catoid"]), str(row["poid"])
        title = str(row["title"] or "")
        url = str(row["absolute_url"])
        outcome.processed += 1
        try:
            ok = _process_program(
                cfg,
                db,
                orch,
                layout,
                row,
                taken,
                catalogue_year=outcome.catalogue_year,
            )
        except HumanVerificationRequired as e:
            outcome.stopped_reason = str(e.instructions)
            log.error("STOPPED at %s: %s", title, e.instructions)
            break
        except Exception as e:
            db.log_error(
                stage="extraction",
                program_name=title,
                source_url=url,
                program_identifier=f"poid={poid}",
                error_type=type(e).__name__,
                error_message=str(e),
                retryable=True,
            )
            db.ensure_program_row(catoid, poid)
            db.mark_program(catoid, poid, ExtractionStatus.FAILED)
            outcome.failed += 1
            log.warning("FAILED %s: %s: %s", title, type(e).__name__, e)
            continue
        if ok:
            outcome.succeeded += 1
        else:
            outcome.failed += 1
        if outcome.processed % 10 == 0:
            regenerate_all(db, root, run_id, cfg)

    # ---------------------------------------------------------------- finish
    result_summary = {
        "run_id": run_id,
        "completed_at": utcnow_iso(),
        "processed": outcome.processed,
        "succeeded": outcome.succeeded,
        "failed": outcome.failed,
        "included_total": outcome.included,
        "stopped_reason": outcome.stopped_reason or "completed",
    }
    db.set_kv("smoke_test_results" if smoke else "full_run_results", result_summary)
    problems = db.verify_outputs(layout.programs)
    outcome.problems = [json.dumps(p) for p in problems]
    if problems:
        log.warning("Output verification found %d problems", len(problems))
    return outcome


def _process_program(
    cfg: config.ScraperConfig,
    db: StateDB,
    orch: AcquisitionOrchestrator,
    layout: config.OutputLayout,
    row,
    taken: set[str],
    catalogue_year: str,
) -> bool:
    catoid, poid = str(row["catoid"]), str(row["poid"])
    title = str(row["title"] or "")
    url = str(row["absolute_url"])
    label = f"program_{poid}"
    db.ensure_program_row(catoid, poid)

    result = orch.acquire(url, PageKind.PROGRAM_PAGE, label=label)
    if not result.ok:
        db.log_error(
            stage="program_acquisition",
            program_name=title,
            source_url=url,
            program_identifier=f"poid={poid}",
            error_type=result.mode.value,
            error_message=str(result.error or result.semantic_evidence)[:1500],
            acquisition_mode=result.mode.value,
            retryable=result.mode
            in (AcquisitionMode.NETWORK_FAILURE, AcquisitionMode.INVALID_CONTENT),
        )
        db.mark_program(catoid, poid, ExtractionStatus.FAILED)
        return False

    # Verify the page belongs to the selected catalogue and program.
    final_params = params_of(result.final_url or url)
    if final_params.get("catoid") not in ("", catoid) or final_params.get("poid") not in ("", poid):
        db.log_error(
            stage="program_verification",
            program_name=title,
            source_url=url,
            program_identifier=f"poid={poid}",
            error_type="wrong_page",
            error_message=f"final URL {result.final_url} does not match catoid={catoid}, poid={poid}",
            acquisition_mode=result.mode.value,
            retryable=True,
        )
        db.mark_program(catoid, poid, ExtractionStatus.FAILED)
        return False

    soup = BeautifulSoup(result.html, "lxml")
    try:
        container, container_evidence = select_main_container(
            soup, cfg, require_content_region=True
        )
    except ContentRegionNotFound as e:
        # Never fall back to the whole document: that is exactly how site
        # navigation and header tables were written into 158 output files
        # (incident 2026-07-30). Record it and keep the program pending so a
        # later attempt / browser render can supply a real content region.
        db.log_error(
            stage="extraction",
            program_name=title,
            source_url=url,
            program_identifier=f"poid={poid}",
            error_type="content_region_not_found",
            error_message=f"{e} | candidates: {e.candidates_seen}",
            acquisition_mode=result.mode.value,
            retryable=True,
        )
        log.warning("NO CONTENT REGION for %s (%s) - not written", title, result.mode.value)
        db.mark_program(catoid, poid, ExtractionStatus.INCOMPLETE)
        return False
    breadcrumbs = capture_breadcrumbs(soup)
    meta = extract_metadata(
        soup,
        container,
        url,
        canonical_url=str(row["canonical_url"]),
        catoid=catoid,
        poid=poid,
        catalogue_year=catalogue_year,
        cfg=cfg,
    )

    # Reconcile classification with page evidence (official page title).
    prelim_cls = Classification(str(row["classification"]))
    from usc_catalog_scraper.models import ClassificationResult

    prelim = ClassificationResult(prelim_cls, str(row["class_reason"] or ""), {})
    final_cls = reconcile_with_page_evidence(prelim, meta.program_name, breadcrumbs, cfg)
    if final_cls.classification is not Classification.INCLUDED:
        db.record_classification(catoid, poid, final_cls)
        with db.tx() as c:
            c.execute("DELETE FROM programs WHERE catoid=? AND poid=?", (catoid, poid))
        log.info(
            "Reclassified after page evidence: %s -> %s (%s)",
            title,
            final_cls.classification.value,
            final_cls.reason,
        )
        return False

    cleaned = clean_content(container, cfg)
    content_text = render_text(cleaned, cfg)
    # Gate on the text that is about to be written, not on the page it came
    # from. A failed extraction must never be saved as a valid result.
    text_ok, text_evidence = validate_extracted_text(content_text, meta.program_name or title)
    if not text_ok:
        db.log_error(
            stage="output_validation",
            program_name=title,
            source_url=url,
            program_identifier=f"poid={poid}",
            error_type="invalid_extracted_text",
            error_message=(
                f"{text_evidence['ok_reason']} | chars={text_evidence['body_chars']} "
                f"| container={container_evidence} "
                f"| excerpts={text_evidence.get('fatal_excerpts', [])[:2]}"
            ),
            acquisition_mode=result.mode.value,
            retryable=True,
        )
        log.warning(
            "REJECTED extraction for %s: %s (existing valid output, if any, kept)",
            title,
            text_evidence["ok_reason"],
        )
        db.mark_program(catoid, poid, ExtractionStatus.INCOMPLETE)
        return False

    meta.acquisition_mode = result.mode.value
    meta.retrieved_at = result.retrieved_at
    meta.extraction_status = ExtractionStatus.COMPLETE.value
    meta.content_sha256 = sha256_text(content_text)
    if not meta.program_name:
        meta.program_name = title

    filename = db.reserve_filename(
        catoid,
        poid,
        build_filename(int(row["seq"]), meta.program_name or title, meta.credential, poid, taken),
    )
    taken.add(filename)
    path = layout.programs / filename
    file_content = compose_program_file(meta, content_text)
    atomic_write_text(path, file_content)
    file_hash = sha256_file(path)

    content_body = content_text.rstrip("\n")
    db.mark_program(
        catoid,
        poid,
        ExtractionStatus.COMPLETE,
        program_name=meta.program_name,
        credential=meta.credential,
        school=meta.school,
        catalogue_year=catalogue_year,
        acquisition_mode=result.mode.value,
        retrieved_at=result.retrieved_at,
        # content_sha256 = rendered content only (matches the .txt header and
        # tracks USC's text); file_sha256 = whole file, used by resume.
        content_sha256=meta.content_sha256,
        file_sha256=file_hash,
        source_html_sha256=result.raw_html_sha256,
        rendered_dom_sha256=result.rendered_dom_sha256,
        char_count=len(content_body),
        line_count=content_body.count("\n") + 1,
        breadcrumbs=breadcrumbs,
    )
    db.mark_errors_resolved(url)
    log.info("Saved %s (%s)", filename, result.mode.value)
    return True
