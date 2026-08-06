"""Logging setup: console (rich when available) plus optional run_log.txt file."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure the package logger. Safe to call more than once."""
    logger = logging.getLogger("usc_catalog_scraper")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False

    # Reset handlers so repeated CLI invocations do not duplicate output.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    console: logging.Handler
    try:
        from rich.logging import RichHandler

        console = RichHandler(rich_tracebacks=False, show_path=False, markup=False)
        console.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    except Exception:  # pragma: no cover - rich is a declared dependency
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))
        logger.addHandler(fh)

    return logger


def get_logger(name: str = "") -> logging.Logger:
    base = "usc_catalog_scraper"
    return logging.getLogger(f"{base}.{name}" if name else base)
