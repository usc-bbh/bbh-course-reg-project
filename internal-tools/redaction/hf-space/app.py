"""
Streamlit front end for the STARS report redactor (student-facing).

Privacy design: the uploaded PDF is redacted entirely IN MEMORY via
`engine.redact_bytes` and is never written to the server's disk. Only the
redacted copy is offered back to the student for download; nothing is stored.

Deployment: Hugging Face Space (Streamlit SDK). Set a Space secret named
APP_PASSPHRASE to the access phrase before going live.
"""
import os

import streamlit as st

from redactors import engine

PASSPHRASE = os.environ.get("APP_PASSPHRASE", "")

st.set_page_config(page_title="STARS Report Redactor", page_icon="🛡️",
                   layout="centered")

st.title("🛡️ STARS Report Redactor")
st.caption("Remove your personal information and grades from a USC STARS "
           "Degree Progress Report before sharing it with the BUAI Builder Hub (BBH).")

with st.expander("What this does and how your file is handled", expanded=True):
    st.markdown(
        "- **Removes** your name, student ID, mailing address, and sport/team.\n"
        "- **Replaces every grade** with a pass/fail marker and **blanks out GPA** figures.\n"
        "- Your uploaded file is processed **in memory on the server and is never "
        "saved or logged** — only you receive the redacted copy.\n"
        "- This is redaction, **not perfect anonymization**: your major, terms, and "
        "course list remain, which could be identifying in a small program. "
        "Please share only if you consent."
    )

with st.expander("How to download your STARS report (PDF)"):
    st.markdown(
        "1. Go to **experience.usc.edu** and open **My Academics**.\n"
        "2. Open your **STARS** (Degree Progress) report.\n"
        "3. Click the **red Print button** at the top of the report.\n"
        "4. In the print dialog, set the destination to **Save as PDF** and save the file.\n"
        "5. Upload that saved PDF below."
    )

# --- access gate -----------------------------------------------------------
if not PASSPHRASE:
    st.error("This app isn't configured yet (no access phrase set). "
             "Please contact the team.")
    st.stop()

entered = st.text_input("Access phrase", type="password",
                        help="Provided to you by the BBH team.")
if entered.strip() != PASSPHRASE:
    if entered:
        st.warning("That access phrase isn't right. Please try again.")
    st.stop()

# --- redaction flow --------------------------------------------------------
consent = st.checkbox(
    "I consent to share my redacted STARS report with the BUAI Builder Hub (BBH).")

uploaded = st.file_uploader(
    "Upload your STARS report (the PDF you saved from experience.usc.edu)",
    type=["pdf"], accept_multiple_files=False)

if uploaded is not None and not consent:
    st.info("Please check the consent box above to proceed.")

if uploaded is not None and consent:
    with st.spinner("Redacting…"):
        res, out = engine.redact_bytes(uploaded.getvalue(), {"pii", "grades"})

    status = res["status"]
    if status in ("REDACTED", "REVIEW") and out:
        g = res.get("grades", {})
        st.success("Done — your redacted report is ready below.")
        st.write(
            f"Removed **{len(res.get('pii', {}))}** identifier field(s), "
            f"**{g.get('grades_replaced', 0)}** grade(s), and "
            f"**{g.get('gpa_replaced', 0)}** GPA/points figure(s)."
        )
        if res.get("fragments"):
            st.info("Part of your name may still appear inside a course title; "
                    "the team will double-check before use.")

        stem = os.path.splitext(uploaded.name)[0]
        stem = stem.replace("DONOTSHARE_", "").replace("REDACTED_", "")
        st.download_button("⬇️ Download redacted PDF", data=out,
                           file_name=f"REDACTED_{stem}.pdf",
                           mime="application/pdf")
        st.caption("Download it, open it to confirm it looks right, then send it "
                   "to the team as instructed.")

    elif status == "SKIPPED":
        st.error("This PDF looks like a **scan** (it has no text layer), so it "
                 "can't be redacted here. Please use the PDF you save via the "
                 "**Print → Save as PDF** steps above on experience.usc.edu, "
                 "rather than a scanned or photographed copy.")
    else:
        st.error("The redaction could not be fully verified, so **no file was "
                 "produced**. Please contact the team — and do not share the "
                 "original in the meantime.")

st.divider()
st.caption("Internal tool of the BUAI Builder Hub (BBH) / BBHCourseReg project. "
           "Processing happens in memory; no files are stored.")
