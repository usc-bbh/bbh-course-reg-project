"""Centralized configuration: tunables, credential vocabularies, detection signals.

Everything that classifies, detects, or filters lives here so behavior is auditable
and adjustable without touching logic modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_START_URL = "https://catalogue.usc.edu/content.php?catoid=22&navoid=9396"
CATALOGUE_HOST = "catalogue.usc.edu"

# Realistic desktop browser user agent for the direct HTTP layer.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Paths disallowed by https://catalogue.usc.edu/robots.txt (fetched 2026-07-09).
# The HTTP layer refuses to request these.
ROBOTS_DISALLOWED_PATHS: tuple[str, ...] = (
    "/portfolio.php",
    "/portfolio_nopop.php",
    "/ajax/",
    "/search_advanced.php",
)

# ---------------------------------------------------------------------------
# Credential vocabularies (token-aware; see classification.py)
# ---------------------------------------------------------------------------

# Undergraduate credential acronyms. Matched case-sensitively as whole tokens.
UNDERGRAD_CREDENTIAL_TOKENS: dict[str, str] = {
    "BA": "Bachelor of Arts",
    "BS": "Bachelor of Science",
    "BFA": "Bachelor of Fine Arts",
    "BM": "Bachelor of Music",
    "BMus": "Bachelor of Music",
    "BArch": "Bachelor of Architecture",
    "BLA": "Bachelor of Landscape Architecture",
    "BSW": "Bachelor of Social Work",
    "BCA": "Bachelor of Communication Arts",
}

# Graduate / professional credential acronyms. Matched case-sensitively as whole
# tokens. Presence in a credential field excludes (or marks combined) a program.
GRADUATE_CREDENTIAL_TOKENS: dict[str, str] = {
    "MA": "Master of Arts",
    "MS": "Master of Science",
    "MBA": "Master of Business Administration",
    "MAcc": "Master of Accounting",
    "MFA": "Master of Fine Arts",
    "MM": "Master of Music",
    "MPA": "Master of Public Administration",
    "MPH": "Master of Public Health",
    "MPP": "Master of Public Policy",
    "MUP": "Master of Urban Planning",
    "MRED": "Master of Real Estate Development",
    "MAT": "Master of Arts in Teaching",
    "MSW": "Master of Social Work",
    "MHA": "Master of Health Administration",
    "MCG": "Master of Communication Management",
    "LLM": "Master of Laws",
    "EdD": "Doctor of Education",
    "PhD": "Doctor of Philosophy",
    "DMA": "Doctor of Musical Arts",
    "DSW": "Doctor of Social Work",
    "DPT": "Doctor of Physical Therapy",
    "DNP": "Doctor of Nursing Practice",
    "OTD": "Doctor of Occupational Therapy",
    "AuD": "Doctor of Audiology",
    "DrPH": "Doctor of Public Health",
    "JD": "Juris Doctor",
    "PharmD": "Doctor of Pharmacy",
    "DDS": "Doctor of Dental Surgery",
    "MD": "Doctor of Medicine",
}

# Spelled-out credential phrases (case-insensitive regex fragments).
UNDERGRAD_CREDENTIAL_PHRASES: tuple[str, ...] = (
    r"bachelor of [a-z][a-z ]+",
    r"bachelor['’]s degree",
)
GRADUATE_CREDENTIAL_PHRASES: tuple[str, ...] = (
    r"master of [a-z][a-z ]+",
    r"master['’]s degree",
    r"doctor of [a-z][a-z ]+",
    r"doctorate",
    r"juris doctor",
    r"graduate certificate",
)

# Program-category phrases that exclude regardless of credential tokens.
# Checked against the normalized title / category labels, not free prose.
# Minor patterns run against the CREDENTIAL-STRIPPED base title so interior
# words ("Asia Minor Studies (BA)") never exclude a bachelor program.
MINOR_PATTERNS: tuple[str, ...] = (r"\bminor\b\s*$", r"\bminor in\b")
CERTIFICATE_PATTERNS: tuple[str, ...] = (r"\bcertificate\b",)
PROGRESSIVE_PATTERNS: tuple[str, ...] = (r"\bprogressive degree\b",)
JOINT_PATTERNS: tuple[str, ...] = (r"\bjoint degree\b", r"\bjoint (?:ba|bs|ma|ms|jd|mba)\b")
DUAL_PATTERNS: tuple[str, ...] = (r"\bdual degree\b", r"\bdual-degree\b")
# "combined" excludes only when it denotes a cross-level degree combination.
# A "combined major" awarding a single bachelor's degree remains eligible.
COMBINED_DEGREE_PATTERNS: tuple[str, ...] = (
    r"\bcombined (?:bachelor|undergraduate).{0,40}(?:master|graduate)\b",
    r"\bcombined degree\b",
    r"\b(?:bachelor|ba|bs)\s*(?:/|\+|and)\s*(?:master|ma|ms|mba)\b",
)
NON_DEGREE_PATTERNS: tuple[str, ...] = (
    r"\bnon-degree\b",
    r"\bpre-professional emphasis\b",
)

# ---------------------------------------------------------------------------
# Challenge / verification detection signals
# ---------------------------------------------------------------------------

CHALLENGE_TEXT_MARKERS: tuple[str, ...] = (
    "javascript is disabled",
    "verify that you are not a robot",
    "just a moment",
    "checking your browser",
    "verify you are human",
    "verifying you are human",
    "enable javascript and cookies to continue",
    "pardon our interruption",
    "request unsuccessful",
    "access denied",
    "press & hold",
    "captcha",
)
CHALLENGE_TITLE_MARKERS: tuple[str, ...] = (
    "just a moment",
    "attention required",
    "access denied",
    "human verification",
    "security check",
)
CHALLENGE_SCRIPT_MARKERS: tuple[str, ...] = (
    "challenge-platform",
    "cf-chl",
    "cf_chl_opt",
    "_incapsula_resource",
    "incapsula",
    "px-captcha",
    "perimeterx",
    "datadome",
    "hcaptcha.com",
    "recaptcha/api.js",
    "turnstile",
    "queue-it",
    "awswaf",
    "token.awswaf",
)

# ---------------------------------------------------------------------------
# Boundary / heading recognition
# ---------------------------------------------------------------------------

TARGET_SECTION_HEADING = "Undergraduate Programs"

# Vendor-specific heading signals: (name, tag names, class regex, effective level).
# Generic native h1-h6 and role="heading" elements are always recognized in
# addition to these. Populated from Modern Campus Catalog (Acalog) conventions;
# `inspect` reports every candidate so this list can be extended from evidence.
VENDOR_HEADING_SIGNALS: tuple[dict, ...] = (
    {
        # NOTE: deliberately narrow. Generic classes like "degree-type" proved
        # to false-positive on decorative credential badges during adversarial
        # review, silently truncating the section. `inspect` reports every
        # candidate heading so this list can be extended from live evidence.
        "name": "acalog-filter-heading",
        "tags": ("p", "div", "td", "span"),
        "class_regex": r"(?:^|\b)(?:acalog[-_][\w-]*heading|filter[-_]heading)(?:\b|$)",
        "level": 2,
    },
    {
        "name": "block-content-strong-label",
        # A <p>/<td> whose ONLY meaningful child is <strong>/<b> acting as a
        # visual section label. Used only when native headings are absent inside
        # the main content container (documented structural fallback).
        "tags": ("p", "td", "div"),
        "class_regex": None,
        "level": 3,
        "strong_label_fallback": True,
    },
)

# Query parameters that never distinguish one program from another.
STRIP_QUERY_PARAMS: tuple[str, ...] = ("returnto", "print", "hl", "expand")
STRIP_QUERY_PARAM_PREFIXES: tuple[str, ...] = ("utm_", "fb", "gclid")

PROGRAM_URL_PATH_MARKERS: tuple[str, ...] = ("preview_program.php",)
PROGRAM_URL_REQUIRED_PARAMS: tuple[str, ...] = ("catoid", "poid")

# Anchors that are catalogue interface, never program content.
# Prefixes match the START of the href; path markers match only the URL PATH,
# so a program link carrying "#fragment" or "returnto=portfolio.php" survives.
INTERFACE_LINK_PREFIXES: tuple[str, ...] = ("#", "javascript:", "mailto:", "tel:")
INTERFACE_PATH_MARKERS: tuple[str, ...] = (
    "portfolio.php",
    "portfolio_nopop.php",
    "print_degree_planner",
)

# ---------------------------------------------------------------------------
# Main-content noise selectors (removed after the content region is chosen)
# ---------------------------------------------------------------------------

NOISE_CSS_SELECTORS: tuple[str, ...] = (
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "form",
    "nav",
    "header",
    "footer",
    "[role=navigation]",
    "[role=banner]",
    "[role=contentinfo]",
    "[role=search]",
    "a[href*='portfolio.php']",
    "a[href*='portfolio_nopop.php']",
    "a[href*='print_degree_planner']",
    ".acalog-portfolio",
    ".social-media",
    ".skip-link",
    "#skip-link",
    ".breadcrumb",
    ".breadcrumbs",
    ".acalog-breadcrumb",
    "#cookie-banner",
    ".cookie-notice",
    ".noprint_pdf",
    # USC gateway chrome observed on the live 2026-2027 pages (2026-07-13):
    # icon-font toolbar (share/print/help/degree-planner buttons render as
    # stray glyphs) and the repeated catalogue-name span above the title.
    ".gateway-toolbar",
    ".acalog-icon",
    ".acalog_catalog_name",
)
# Text lines that are repeated interface chrome, removed by the renderer.
INTERFACE_TEXT_LINES: tuple[str, ...] = (
    "add to portfolio (opens a new window)",
    "add to portfolio",
    "print (opens a new window)",
    "print-friendly page (opens a new window)",
    "print degree planner (opens a new window)",
    "help (opens a new window)",
    "share this page:",
    "back to top",
    "[archived catalogue]",
    # Accordion close buttons left in the DOM after browser-side expansion.
    "close",
    # Direct-HTML variants of the toolbar links (2026-07-13 live evidence).
    "help",
    "print degree planner (opens a new window)",
)


@dataclass
class ScraperConfig:
    """Runtime configuration. CLI options map onto these fields."""

    start_url: str = DEFAULT_START_URL
    output_dir: Path | None = None  # resolved after catalogue year is known
    workdir: Path = field(default_factory=Path.cwd)
    latest_resolution: bool = True
    collect_minors: bool = False
    collect_all_undergrad: bool = False  # bachelor's degrees AND minors
    headed: bool = False
    headless: bool = True
    resume: bool = True
    overwrite: bool = False
    max_programs: int | None = None
    delay_min: float = 3.5
    delay_max: float = 7.5
    max_retries: int = 4
    save_raw_html: bool = False
    save_rendered_html: bool = False
    save_failure_screenshots: bool = True
    browser_profile_dir: Path | None = None
    catalogue_year: str | None = None
    strict: bool = True
    verbose: bool = False
    boundary_heading: str = TARGET_SECTION_HEADING
    allow_browser: bool = True  # tests can disable the Playwright layer

    # HTTP tuning
    connect_timeout: float = 15.0
    read_timeout: float = 40.0
    write_timeout: float = 15.0
    pool_timeout: float = 15.0
    max_connections: int = 2

    # Browser launch tuning
    chromium_sandbox: bool = True  # disable only in containers without userns
    browser_extra_args: tuple[str, ...] = ()

    # Browser readiness tuning
    nav_timeout_ms: int = 45_000
    readiness_timeout_ms: int = 30_000
    stabilization_polls: int = 3
    stabilization_interval_ms: int = 700
    challenge_wait_minutes: float = 6.0

    def http_delay_range(self) -> tuple[float, float]:
        lo, hi = sorted((self.delay_min, self.delay_max))
        return (max(0.0, lo), max(0.1, hi))


DEFAULT_CONFIG = ScraperConfig()


@dataclass
class OutputLayout:
    """Resolved output folder layout for one collection run."""

    root: Path
    programs: Path = field(init=False)
    audit_evidence: Path = field(init=False)
    screenshots: Path = field(init=False)
    sample_comparisons: Path = field(init=False)
    raw_pages: Path = field(init=False)
    rendered_pages: Path = field(init=False)
    state_dir: Path = field(init=False)
    browser_profile: Path = field(init=False)

    def __post_init__(self) -> None:
        self.programs = self.root / "programs"
        self.audit_evidence = self.root / "audit_evidence"
        self.screenshots = self.audit_evidence / "screenshots"
        self.sample_comparisons = self.audit_evidence / "sample_comparisons"
        self.raw_pages = self.audit_evidence / "raw_pages"
        self.rendered_pages = self.audit_evidence / "rendered_pages"
        self.state_dir = self.root / "state"
        self.browser_profile = self.state_dir / "browser_profile"

    def create(self) -> None:
        for p in (
            self.programs,
            self.screenshots,
            self.sample_comparisons,
            self.raw_pages,
            self.rendered_pages,
            self.state_dir,
        ):
            p.mkdir(parents=True, exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self.state_dir / "scraper.sqlite3"


def output_root_for_year(
    base: Path, catalogue_year: str | None, prefix: str = "usc_undergraduate_catalogue"
) -> Path:
    """usc_undergraduate_catalogue_2026_2027 / usc_minors_catalogue_2026_2027 folder name."""
    year = (catalogue_year or "unknown_year").replace("-", "_").replace("/", "_")
    return base / f"{prefix}_{year}"
