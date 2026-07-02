"""Shared machinery for every redaction pass.

A *finding* is a dict describing one glyph region to remove and what to put
back:

    {
      "page": int,             # 0-based page index
      "rect": fitz.Rect,       # glyphs to TRULY remove (apply_redactions)
      "box":  fitz.Rect,       # region to fit the replacement text into
      "text": str,             # replacement (width-preserving filler / token)
    }

Every pass produces findings; `apply_and_fill` removes then re-inserts them in
one shot, so the fixed-width column structure of the report is preserved and
the original glyphs are genuinely gone (not merely covered).
"""
import fitz


def has_text_layer(doc):
    """True if the PDF has any extractable text (i.e. not a pure scan)."""
    return sum(len(p.get_text("text")) for p in doc) > 0


def page_texts(doc):
    return [p.get_text("text") for p in doc]


def _insert_fit(page, box, text):
    """Insert monospace `text` sized to fill `box` (Courier => same pitch as
    the surrounding fixed-width report text)."""
    n = max(len(text), 1)
    fs = min((box.width / n) / 0.6, box.height)
    page.insert_text((box.x0, box.y1 - box.height * 0.18), text,
                     fontname="cour", fontsize=fs, color=(0, 0, 0))


def apply_and_fill(doc, findings):
    """Remove every finding's glyphs, then re-insert its replacement text."""
    for f in findings:
        doc[f["page"]].add_redact_annot(f["rect"], fill=(1, 1, 1))
    for page in doc:
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
    for f in findings:
        _insert_fit(doc[f["page"]], f.get("box") or f["rect"], f["text"])


def scrub_metadata(doc):
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:
        pass
