"""Core redaction engine, shared by the CLI (`redact_stars.py`) and the
in-browser/hosted app.

`redact_doc` runs the selected passes on an open PyMuPDF document IN PLACE and
returns a status dict; it does NOT save or close (the caller decides where the
bytes go). `redact_bytes` is the in-memory wrapper the hosted app uses so an
uploaded file is never written to the server's disk.
"""
import fitz

from . import common, pii, grades


def existing_modes(name):
    """What has ALREADY been redacted in a file, inferred from its name."""
    b = str(name).upper()
    # match on the basename only
    b = b.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if b.startswith("REDACTED-PII_"):
        return {"pii"}
    if b.startswith("REDACTED-GRADES_"):
        return {"grades"}
    if b.startswith("REDACTED_"):
        return {"pii", "grades"}
    return set()


def redact_doc(doc, modes, tag=False, existing=frozenset()):
    """Run the selected passes on `doc` in place. Returns a status dict.
    Does NOT save or close the document.

    status is one of: SKIPPED (no text layer), FAILED (no anchors, or a
    survivor was found in verification), REVIEW (clean but a name fragment
    appears elsewhere), REDACTED (clean)."""
    res = {"status": None, "reason": "", "pii": {}, "grades": {},
           "fragments": [], "hard": [], "pii_note": ""}

    if not common.has_text_layer(doc):
        res["status"] = "SKIPPED"
        res["reason"] = "no text layer (scanned image; needs OCR-based redaction)"
        return res

    findings, metas = [], {}
    if "pii" in modes:
        pf, pm = pii.build_findings(doc, tag=tag)
        if pm["values"]:
            findings += pf
            metas["pii"] = pm
            res["pii"] = pm["values"]
        elif "pii" in existing:
            res["pii_note"] = "already PII-redacted — PII pass skipped"
        else:
            res["status"] = "FAILED"
            res["reason"] = "text present but no STARS identifiers detected"
            return res
    if "grades" in modes:
        gf, gm = grades.build_findings(doc)
        findings += gf
        metas["grades"] = gm
        res["grades"] = gm

    common.apply_and_fill(doc, findings)
    common.scrub_metadata(doc)

    hard, soft = [], []
    if "pii" in metas:
        h, s = pii.verify(doc, metas["pii"])
        hard += h
        soft += s
    if "grades" in metas:
        h, s = grades.verify(doc, metas["grades"])
        hard += h
        soft += s
    res["fragments"] = soft

    if hard:
        res["status"] = "FAILED"
        res["reason"] = "verification failed — output withheld"
        res["hard"] = hard
        return res

    res["status"] = "REVIEW" if soft else "REDACTED"
    return res


def redact_bytes(data, modes, tag=False, existing=frozenset()):
    """Redact a PDF held in memory. Returns (status_dict, output_bytes_or_None).
    The input bytes are never written to disk; output is produced in memory and
    only returned on REDACTED/REVIEW."""
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        res = redact_doc(doc, modes, tag=tag, existing=existing)
        out = None
        if res["status"] in ("REDACTED", "REVIEW"):
            out = doc.tobytes(garbage=4, deflate=True, clean=True)
        return res, out
    finally:
        doc.close()
