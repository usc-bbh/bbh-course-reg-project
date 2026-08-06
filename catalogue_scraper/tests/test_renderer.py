"""Deterministic text renderer tests."""

from bs4 import BeautifulSoup

from usc_catalog_scraper.text_renderer import render_text


def render(html: str) -> str:
    soup = BeautifulSoup(f"<div id='root'>{html}</div>", "lxml")
    return render_text(soup.find(id="root"))


def test_headings_and_paragraph_spacing():
    out = render("<h2>Degree Requirements</h2><p>Total: 128 units.</p>")
    assert "## Degree Requirements" in out
    assert out.index("## Degree Requirements") < out.index("Total: 128 units.")
    assert "\n\n" in out


def test_unordered_nesting_preserved():
    out = render(
        "<ul><li>Core courses<ul><li>PHIL 100 (4 units)</li><li>PHIL 222 (4 units)</li></ul></li>"
        "<li>Electives</li></ul>"
    )
    lines = out.strip().split("\n")
    assert lines[0] == "- Core courses"
    assert lines[1] == "  - PHIL 100 (4 units)"
    assert lines[2] == "  - PHIL 222 (4 units)"
    assert lines[3] == "- Electives"


def test_ordered_numbering_with_start_and_nesting():
    out = render(
        '<ol start="3"><li>Third item</li><li>Fourth item<ol><li>Sub one</li></ol></li></ol>'
    )
    lines = out.strip().split("\n")
    assert lines[0] == "3. Third item"
    assert lines[1] == "4. Fourth item"
    assert lines[2] == "  1. Sub one"


def test_table_rendering_with_caption_and_headers():
    out = render(
        "<table><caption>Required Courses</caption>"
        "<tr><th>Course</th><th>Title</th><th>Units</th></tr>"
        "<tr><td>ACCT 410</td><td>Foundations of Accounting</td><td>4</td></tr>"
        "<tr><td>ACCT 411</td><td>Advanced Accounting</td><td>4</td></tr></table>"
    )
    assert "TABLE: Required Courses" in out
    assert "Columns: Course | Title | Units" in out
    assert "Row 1: ACCT 410 | Foundations of Accounting | 4" in out
    assert "Row 2: ACCT 411 | Advanced Accounting | 4" in out


def test_rowspan_and_colspan_expansion():
    out = render(
        "<table><tr><th>Track</th><th>Course</th><th>Units</th></tr>"
        '<tr><td rowspan="2">Audit</td><td>ACCT 462</td><td>4</td></tr>'
        "<tr><td>ACCT 463</td><td>4</td></tr>"
        '<tr><td colspan="2">Total</td><td>8</td></tr></table>'
    )
    assert "Row 1: Audit | ACCT 462 | 4" in out
    assert "Row 2: Audit | ACCT 463 | 4" in out  # rowspan value repeated, not lost
    assert "Row 3: Total | Total | 8" in out  # colspan expanded without ambiguity


def test_footnote_sup_preserved_and_connected():
    out = render(
        "<p>PHIL 430 Ethics (4 units) <sup>1</sup></p><p><sup>1</sup> Requires junior standing.</p>"
    )
    assert "PHIL 430 Ethics (4 units) [1]" in out
    assert "[1] Requires junior standing." in out


def test_informative_external_link_url_appended():
    out = render(
        '<p>See the <a href="https://dornsife.usc.edu/phil/scholarships">scholarship page</a>.</p>'
    )
    assert "scholarship page [https://dornsife.usc.edu/phil/scholarships]" in out


def test_catalogue_internal_links_render_text_only():
    out = render(
        '<p><a href="preview_course_nopop.php?catoid=22&coid=1">PHIL 100 The Big Questions</a> (4 units)</p>'
    )
    assert "PHIL 100 The Big Questions (4 units)" in out
    assert "preview_course_nopop" not in out


def test_interface_text_lines_removed():
    out = render("<p>Add to Portfolio (opens a new window)</p><p>Real requirement text.</p>")
    assert "Add to Portfolio" not in out
    assert "Real requirement text." in out


def test_definition_list_rendering():
    out = render(
        "<dl><dt>Residency</dt><dd>20 units at USC</dd><dt>GPA</dt><dd>2.0 minimum</dd></dl>"
    )
    lines = out.strip().split("\n")
    assert lines[0] == "Residency:"
    assert lines[1] == "  20 units at USC"
    assert lines[2] == "GPA:"


def test_br_becomes_meaningful_line_break():
    out = render("<p>Line one<br>Line two</p>")
    assert "Line one\nLine two" in out


def test_unix_newlines_and_single_trailing_newline():
    out = render("<p>alpha</p><p>beta</p>")
    assert "\r" not in out
    assert out.endswith("\n") and not out.endswith("\n\n")


def test_whitespace_collapse_and_entities():
    out = render("<p>Total&nbsp;&nbsp;units:&amp;   128</p>")
    assert "Total units:& 128" in out


def test_hidden_accordion_content_is_rendered():
    out = render(
        '<div class="acalog-panel" style="display:none"><ul><li>DES 320 Interaction Design (4 units)</li></ul></div>'
    )
    assert "DES 320 Interaction Design (4 units)" in out


def test_deterministic_output():
    html = "<h2>R</h2><ul><li>a</li><li>b</li></ul><table><tr><td>1</td></tr></table>"
    assert render(html) == render(html)
