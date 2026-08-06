"""Deterministic HTML-to-plain-text renderer for catalogue requirement content.

Rules (see project spec): heading hierarchy, paragraph order, ordered-list
numbering, nested indentation, definition lists, meaningful line breaks,
explicit table representation with colspan/rowspan expansion, course codes and
units preserved, informative link URLs appended, interface text removed,
Unix newlines, single trailing newline, UTF-8 without lossy replacement.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from bs4 import NavigableString, Tag

from usc_catalog_scraper import config

_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "aside",
    "blockquote",
    "pre",
    "ul",
    "ol",
    "dl",
    "table",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "fieldset",
    "figure",
    "figcaption",
    "address",
    "center",
    "tbody",
    "thead",
    "tfoot",
    "tr",
    "td",
    "th",
    "li",
    "dt",
    "dd",
    "form",
    "details",
    "summary",
}
_SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "button",
    "input",
    "select",
    "label",
}

_CATALOGUE_INTERNAL_PATH_MARKERS = (
    "preview_program.php",
    "preview_course",
    "content.php",
    "index.php",
    "portfolio",
    "search.php",
    "print_degree_planner",
    "catalog_list.php",
    "help.php",
)


def _collapse(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text.replace(" ", " "))


def _informative_href(href: str, link_text: str) -> bool:
    href = (href or "").strip()
    if not href or href.startswith(("#", "javascript:", "mailto:")):
        return False
    parts = urlsplit(href)
    if parts.scheme not in ("http", "https"):
        return False
    if any(
        marker in (parts.path + "?" + parts.query) for marker in _CATALOGUE_INTERNAL_PATH_MARKERS
    ):
        return False
    cleaned_text = link_text.strip().rstrip("/").lower()
    cleaned_href = href.rstrip("/").lower()
    return not (cleaned_text and cleaned_text in cleaned_href)


def _inline_text(el: object, keep_breaks: bool = True) -> str:
    """Render inline content: text, links, <br>, <sup> footnote markers."""
    if isinstance(el, NavigableString):
        return _collapse(str(el))
    if not isinstance(el, Tag):
        return ""
    if el.name in _SKIP_TAGS:
        return ""
    if el.name == "br":
        return "\n" if keep_breaks else " "
    if el.name == "a":
        inner = "".join(_inline_text(c, keep_breaks) for c in el.children)
        inner = inner.strip()
        href = str(el.get("href") or "")
        if inner and _informative_href(href, inner):
            return f"{inner} [{href}]"
        return inner
    if el.name == "sup":
        inner = "".join(_inline_text(c, keep_breaks) for c in el.children).strip()
        # Short footnote markers stay visibly connected: "PHIL 430 ... [1]".
        if 0 < len(inner) <= 4:
            return f"[{inner}]"
        return inner
    if el.name in ("ul", "ol", "table", "dl"):
        # Handled by block logic; inline call sites replace with a marker space.
        return " "
    parts = [_inline_text(c, keep_breaks) for c in el.children]
    return "".join(parts)


def _tidy_inline(text: str) -> str:
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines]
    out = "\n".join(lines)
    out = re.sub(r"\n{2,}", "\n", out)
    return out.strip()


class _Renderer:
    def __init__(self, cfg: config.ScraperConfig | None = None):
        self.cfg = cfg or config.DEFAULT_CONFIG
        self.blocks: list[str] = []

    # ------------------------------------------------------------------
    def render(self, root: Tag) -> str:
        self.blocks = []
        self._children_as_blocks(root)
        text = "\n\n".join(b for b in self.blocks if b.strip())
        text = self._strip_interface_lines(text)
        text = re.sub(r"[ \t]+$", "", text, flags=re.M)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip("\n") + "\n"

    # ------------------------------------------------------------------
    def _strip_interface_lines(self, text: str) -> str:
        markers = {m.casefold() for m in config.INTERFACE_TEXT_LINES}
        kept: list[str] = []
        for line in text.split("\n"):
            s = line.strip().casefold()
            if s in markers:
                continue
            # Direct-HTML pages join interface links on one line
            # ("Print Degree Planner (...) | Print-Friendly Page (...)").
            parts = [p.strip() for p in s.split("|") if p.strip()]
            if len(parts) > 1 and all(p in markers for p in parts):
                continue
            kept.append(line)
        return "\n".join(kept)

    # ------------------------------------------------------------------
    def _children_as_blocks(self, el: Tag) -> None:
        inline_buffer: list[str] = []

        def flush() -> None:
            if inline_buffer:
                text = _tidy_inline("".join(inline_buffer))
                if text:
                    self.blocks.append(text)
                inline_buffer.clear()

        for child in el.children:
            if isinstance(child, NavigableString):
                inline_buffer.append(_inline_text(child))
                continue
            if not isinstance(child, Tag):
                continue
            if child.name in _SKIP_TAGS:
                continue
            if child.name in _BLOCK_TAGS:
                flush()
                self._block(child)
            else:
                inline_buffer.append(_inline_text(child))
        flush()

    # ------------------------------------------------------------------
    def _block(self, el: Tag) -> None:
        name = el.name
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = _tidy_inline(_inline_text(el, keep_breaks=False))
            if text:
                self.blocks.append(f"{'#' * int(name[1])} {text}")
            return
        if name == "hr":
            self.blocks.append("---")
            return
        if name in ("ul", "ol"):
            lines = self._list_lines(el, depth=0)
            if lines:
                self.blocks.append("\n".join(lines))
            return
        if name == "dl":
            lines = self._dl_lines(el)
            if lines:
                self.blocks.append("\n".join(lines))
            return
        if name == "table":
            if self._is_layout_table(el):
                # Single-column/presentation tables carry no tabular
                # relations; they are page scaffolding (the live catalogue
                # nests all content in table_default chrome). Render their
                # cells as normal block flow instead of flattening the whole
                # page into one table row.
                for tr in [t for t in el.find_all("tr") if t.find_parent("table") is el]:
                    for cell in tr.children:
                        if isinstance(cell, Tag) and cell.name in ("td", "th"):
                            self._children_as_blocks(cell)
                return
            block = self._table_block(el)
            if block:
                self.blocks.append(block)
            return
        if name == "blockquote":
            sub = _Renderer(self.cfg)
            inner = sub.render(el).strip("\n")
            if inner:
                self.blocks.append("\n".join(f"  {ln}" for ln in inner.split("\n")))
            return
        if name == "pre":
            text = el.get_text()
            if text.strip():
                self.blocks.append(text.strip("\n"))
            return
        if name in ("p", "figcaption", "summary", "address", "center"):
            text = _tidy_inline(_inline_text(el))
            if text:
                self.blocks.append(text)
            # A paragraph can still wrap a list/table in bad markup:
            for nested in el.find_all(["ul", "ol", "table", "dl"], recursive=False):
                self._block(nested)
            return
        # Transparent containers: recurse.
        self._children_as_blocks(el)

    # ------------------------------------------------------------------
    def _list_lines(self, el: Tag, depth: int) -> list[str]:
        lines: list[str] = []
        ordered = el.name == "ol"
        try:
            counter = int(str(el.get("start") or "1"))
        except (TypeError, ValueError):
            counter = 1
        items = [c for c in el.children if isinstance(c, Tag) and c.name == "li"]
        for li in items:
            value = li.get("value")
            if ordered and value and str(value).isdigit():
                counter = int(str(value))
            marker = f"{counter}." if ordered else "-"
            indent = "  " * depth
            nested_blocks: list[Tag] = []
            inline_parts: list[str] = []
            for c in li.children:
                if isinstance(c, Tag) and c.name in ("ul", "ol", "table", "dl"):
                    nested_blocks.append(c)
                elif isinstance(c, Tag) and c.name in ("p", "div"):
                    inline_parts.append(_inline_text(c) + "\n")
                else:
                    inline_parts.append(_inline_text(c))
            text = _tidy_inline("".join(inline_parts))
            first, *rest = text.split("\n") if text else [""]
            lines.append(f"{indent}{marker} {first}".rstrip())
            hang = indent + " " * (len(marker) + 1)
            lines.extend(f"{hang}{ln}" for ln in rest if ln)
            for nested in nested_blocks:
                if nested.name in ("ul", "ol"):
                    lines.extend(self._list_lines(nested, depth + 1))
                elif nested.name == "dl":
                    lines.extend(f"{hang}{ln}" for ln in self._dl_lines(nested))
                else:
                    tbl = self._table_block(nested)
                    lines.extend(f"{hang}{ln}" for ln in tbl.split("\n") if ln)
            if ordered:
                counter += 1
        return lines

    # ------------------------------------------------------------------
    def _dl_lines(self, el: Tag) -> list[str]:
        lines: list[str] = []
        for c in el.children:
            if not isinstance(c, Tag):
                continue
            if c.name == "dt":
                text = _tidy_inline(_inline_text(c, keep_breaks=False))
                if text:
                    lines.append(f"{text}:")
            elif c.name == "dd":
                text = _tidy_inline(_inline_text(c))
                for ln in text.split("\n"):
                    if ln:
                        lines.append(f"  {ln}")
        return lines

    # ------------------------------------------------------------------
    def _cell_text(self, cell: Tag) -> str:
        """Single-line cell rendering that preserves block content in cells.

        Lists become "item ; item" (ordered numbering kept), definition lists
        "term: ; value", nested tables "a / b ; c / d" — separators chosen to
        never collide with the outer " | " column delimiter (adversarial
        review findings 12/13).
        """
        parts: list[str] = []
        inline_buf: list[str] = []

        def flush_inline() -> None:
            text = _tidy_inline("".join(inline_buf)).replace("\n", " ").strip()
            inline_buf.clear()
            if text:
                parts.append(text)

        for child in cell.children:
            if isinstance(child, Tag) and child.name in ("ul", "ol"):
                flush_inline()
                items = [
                    re.sub(r"^\s*-\s+", "", ln.strip())
                    for ln in self._list_lines(child, depth=0)
                    if ln.strip()
                ]
                if items:
                    parts.append(" ; ".join(items))
            elif isinstance(child, Tag) and child.name == "dl":
                flush_inline()
                items = [ln.strip() for ln in self._dl_lines(child) if ln.strip()]
                if items:
                    parts.append(" ; ".join(items))
            elif isinstance(child, Tag) and child.name == "table":
                flush_inline()
                inner_rows = [
                    ln.split(": ", 1)[-1].replace(" | ", " / ")
                    for ln in self._table_block(child).split("\n")
                    if ln.startswith(("Row", "Columns"))
                ]
                if inner_rows:
                    parts.append(" ; ".join(inner_rows))
            else:
                inline_buf.append(_inline_text(child))
        flush_inline()
        return " ".join(parts).strip()

    # ------------------------------------------------------------------
    def _is_layout_table(self, table: Tag) -> bool:
        """True when the table expresses layout, not data: role=presentation,
        or every direct row holds at most one cell (no column relations)."""
        if str(table.get("role") or "").lower() == "presentation":
            return True
        rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
        if not rows:
            return True
        for tr in rows:
            cells = [c for c in tr.children if isinstance(c, Tag) and c.name in ("td", "th")]
            if len(cells) > 1:
                return False
        return True

    # ------------------------------------------------------------------
    def _table_block(self, table: Tag) -> str:
        rows = [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]
        if not rows:
            return ""
        grid: dict[tuple[int, int], str] = {}
        max_col = 0
        header_row_idx: int | None = None
        for r, tr in enumerate(rows):
            cells = [c for c in tr.find_all(["td", "th"]) if c.find_parent("tr") is tr]
            if cells and all(c.name == "th" for c in cells) and header_row_idx is None:
                header_row_idx = r
            col = 0
            for cell in cells:
                while (r, col) in grid:
                    col += 1
                text = self._cell_text(cell)
                try:
                    rowspan = max(1, int(str(cell.get("rowspan") or "1")))
                except (TypeError, ValueError):
                    rowspan = 1
                try:
                    colspan = max(1, int(str(cell.get("colspan") or "1")))
                except (TypeError, ValueError):
                    colspan = 1
                for dr in range(rowspan):
                    for dc in range(colspan):
                        grid[(r + dr, col + dc)] = text
                col += colspan
                max_col = max(max_col, col)
        total_rows = max((r for r, _ in grid), default=-1) + 1

        caption_el = table.find("caption")
        caption = _tidy_inline(_inline_text(caption_el, keep_breaks=False)) if caption_el else ""
        lines: list[str] = [
            f"TABLE: {caption}".rstrip().rstrip(":") if not caption else f"TABLE: {caption}"
        ]
        if not caption:
            lines = ["TABLE:"]

        def row_cells(r: int) -> list[str]:
            return [grid.get((r, c), "") for c in range(max_col)]

        body_num = 0
        for r in range(total_rows):
            cell_texts = row_cells(r)
            if not any(c.strip() for c in cell_texts):
                continue
            if r == header_row_idx:
                lines.append("Columns: " + " | ".join(cell_texts))
                continue
            body_num += 1
            lines.append(f"Row {body_num}: " + " | ".join(cell_texts))
        return "\n".join(lines)


def render_text(root: Tag, cfg: config.ScraperConfig | None = None) -> str:
    """Render a cleaned content region to deterministic plain text."""
    return _Renderer(cfg).render(root)
