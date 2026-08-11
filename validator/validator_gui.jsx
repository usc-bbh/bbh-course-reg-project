import React, { useState, useMemo, useEffect, useRef } from "react";
import { parseStarsReport } from "../stars-parser";

// ─────────────────────────────────────────────────────────────
// MOCK CATALOG — shaped like catalog/README.md schema v6.
// Replace with real per-course fetches: /catalog/20263/CSCI-104.json
// ─────────────────────────────────────────────────────────────
const MOCK_CATALOG = {
  "CSCI 103": {
    course_name: "CSCI 103", units: 4, description: "Intro to programming in C/C++.",
    has_lab: true, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "30211", section_type: "lectures", mode: "Lecture", instructor: "Mark Redekopp", days: ["Tue", "Thu"], start_time: "11:00", end_time: "12:20", total_seats: 60, registered_seats: 16, open_seats: 44, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
      labs: [
        { section_id: "30212", section_type: "labs", mode: "Lab", instructor: "TBD", days: ["Wed"], start_time: "12:00", end_time: "12:50", total_seats: 30, registered_seats: 12, open_seats: 18, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
    },
  },
  "CSCI 104": {
    course_name: "CSCI 104", units: 4, description: "Data structures and OOP. Prerequisite: CSCI 103.",
    has_lab: true, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "29903", section_type: "lectures", mode: "Lecture", instructor: "Mark Redekopp", days: ["Mon", "Wed"], start_time: "10:00", end_time: "11:20", total_seats: 120, registered_seats: 108, open_seats: 12, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
      labs: [
        { section_id: "30119", section_type: "labs", mode: "Lab", instructor: "TBD", days: ["Fri"], start_time: "10:00", end_time: "11:50", total_seats: 30, registered_seats: 25, open_seats: 5, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
        { section_id: "29905", section_type: "labs", mode: "Lab", instructor: "TBD", days: ["Fri"], start_time: "14:00", end_time: "15:50", total_seats: 30, registered_seats: 30, open_seats: 0, is_full: true, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
    },
  },
  "CSCI 170": {
    course_name: "CSCI 170", units: 4, description: "Discrete methods in CS. Prerequisite: CSCI 103.",
    has_lab: false, has_discussion: true, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "30121", section_type: "lectures", mode: "Lecture", instructor: "Aaron Cote", days: ["Tue", "Thu"], start_time: "11:00", end_time: "12:20", total_seats: 100, registered_seats: 97, open_seats: 3, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
      discussions: [
        { section_id: "29929", section_type: "discussions", mode: "Discussion", instructor: "TBD", days: ["Fri"], start_time: "09:00", end_time: "09:50", total_seats: 30, registered_seats: 22, open_seats: 8, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
    },
  },
  "MATH 226": {
    course_name: "MATH 226", units: 4, description: "Calculus III. Prerequisite: MATH 126.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "39100", section_type: "lectures", mode: "Lecture", instructor: "N. Kosovalic", days: ["Mon", "Wed"], start_time: "10:00", end_time: "11:20", total_seats: 40, registered_seats: 20, open_seats: 20, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
        { section_id: "39101", section_type: "lectures", mode: "Lecture", instructor: "TBD", days: ["Tue", "Thu"], start_time: "14:00", end_time: "15:20", total_seats: 40, registered_seats: 25, open_seats: 15, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
    },
  },
  "BUAD 311": {
    course_name: "BUAD 311", units: 4, description: "Operations management.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "14911", section_type: "lectures", mode: "Lecture", instructor: "TBD", days: ["Mon", "Wed"], start_time: "08:00", end_time: "09:20", total_seats: 55, registered_seats: 45, open_seats: 10, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
        { section_id: "14913", section_type: "lectures", mode: "Lecture", instructor: "TBD", days: ["Mon", "Wed"], start_time: "12:00", end_time: "13:20", total_seats: 55, registered_seats: 50, open_seats: 5, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
    },
  },
  "ACCT 370": {
    course_name: "ACCT 370", units: 4, description: "Decision-making for accounting professionals.",
    has_lab: false, has_discussion: false, has_d_clearance: true, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "14025", section_type: "lectures", mode: "Lecture", instructor: "Taylor Wiesen", days: ["Tue", "Thu"], start_time: "14:00", end_time: "15:50", total_seats: 44, registered_seats: 44, open_seats: 0, is_full: true, is_cancelled: false, has_d_clearance: true, notes: null, link_code: null },
        { section_id: "14027", section_type: "lectures", mode: "Lecture", instructor: "Taylor Wiesen", days: ["Tue", "Thu"], start_time: "18:00", end_time: "19:50", total_seats: 44, registered_seats: 10, open_seats: 34, is_full: false, is_cancelled: false, has_d_clearance: true, notes: null, link_code: null },
      ],
    },
  },
  "BUAD 494": {
    course_name: "BUAD 494", units: 2, description: "Senior research and thesis.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: true,
    sections: {
      lectures: [
        { section_id: "15124", section_type: "lectures", mode: "Lecture", instructor: "Sriram Dasu", days: ["Mon"], start_time: "17:00", end_time: "18:50", total_seats: 20, registered_seats: 8, open_seats: 12, is_full: false, is_cancelled: false, has_d_clearance: false, notes: "Section 15124 is for Honors Research and Thesis offered by the Data Sciences and Operations Department.", link_code: null },
      ],
    },
  },
  "WRIT 340": {
    course_name: "WRIT 340", units: 4, description: "Advanced writing.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "60100", section_type: "lectures", mode: "Lecture", instructor: "TBD", days: ["Tue", "Thu"], start_time: "09:30", end_time: "10:50", total_seats: 19, registered_seats: 17, open_seats: 2, is_full: false, is_cancelled: false, has_d_clearance: false, notes: null, link_code: null },
      ],
    },
  },
};

// Demo fallback only — used before a real STARS PDF is uploaded, or if
// parsing fails and the student hasn't filled in manual entry yet.
// Matches Avi's real parser output shape exactly (see stars-parser/README.md).
const DEMO_STARS = {
  completedCourses: [{ code: "CSCI103", grade: "A" }, { code: "MATH225", grade: "B+" }, { code: "WRIT150", grade: "A-" }],
  inProgressCourses: [],
  classLevel: "Junior",
};

// ─────────────────────────────────────────────────────────────
// Normalization — every boundary runs codes through this.
// "CSCI103" / "csci 103" / "CSCI-103" → "CSCI 104"-style "PREFIX NNN"
// ─────────────────────────────────────────────────────────────
function normalizeCode(code) {
  const m = String(code).trim().match(/^([A-Za-z]+)[\s-]*(\d+[A-Za-z]*)$/);
  if (!m) return String(code).trim().toUpperCase();
  return `${m[1].toUpperCase()} ${m[2].toUpperCase()}`;
}

const toMin = (t) => {
  if (!t || t === "TBA") return null;
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
};
const fmt = (t) => {
  const [h, m] = t.split(":").map(Number);
  const ampm = h < 12 ? "am" : "pm";
  const hh = h % 12 || 12;
  return m === 0 ? `${hh}${ampm}` : `${hh}:${String(m).padStart(2, "0")}${ampm}`;
};

const allSections = (entry) =>
  entry ? Object.values(entry.sections).flat().filter((s) => !s.is_cancelled) : [];

// ─────────────────────────────────────────────────────────────
// MOCK VALIDATOR — mirrors Tanzil's validate_next_semester().
//
// Input  : planned_courses — [{course: "CSCI 104", sections: ["29903","30119"]}]
//          sections are REQUIRED on every entry (per 4:46am thread — you
//          can't check seats/conflicts/pairing without them, and allowing
//          course-only input means two code paths to maintain).
//          stars_report, course_catalog
// Output : { overall_status, course_results: [{course, status, reasons}], summary }
//
// This is a placeholder. Once Pyodide is wired, this whole function is
// deleted and validate_next_semester() is called directly — the Python
// stays the single source of truth.
// ─────────────────────────────────────────────────────────────
function mockValidate(plannedCourses, starsReport, catalog) {
  const completed = new Set((starsReport.completedCourses || []).map((c) => normalizeCode(c.code)));
  const inProgress = new Set((starsReport.inProgressCourses || []).map((c) => normalizeCode(c.code)));
  const levelOrder = { Freshman: 1, Sophomore: 2, Junior: 3, Senior: 4 };
  const classLevel = starsReport.classLevel;

  const plans = plannedCourses.map((p) => ({ course: p.course, sections: p.sections || [] }));

  // Fail fast rather than silently validating something the student didn't ask for.
  const missing = plans.filter((p) => !p.sections.length).map((p) => p.course);
  if (missing.length) throw new Error(`sections are required for: ${missing.join(", ")}`);

  const resolved = {};
  plans.forEach(({ course, sections }) => {
    const pool = allSections(catalog[normalizeCode(course)]);
    resolved[course] = pool.filter((s) => sections.includes(s.section_id));
  });

  // ── Time conflicts ──
  const conflicts = {};
  const overlap = (a, b) =>
    a.days.some((d) => b.days.includes(d)) &&
    toMin(a.start_time) < toMin(b.end_time) &&
    toMin(b.start_time) < toMin(a.end_time);

  for (let i = 0; i < plans.length; i++) {
    for (let j = i + 1; j < plans.length; j++) {
      const A = plans[i], B = plans[j];
      const sa = resolved[A.course], sb = resolved[B.course];
      if (!sa.length || !sb.length) continue;

      // Sections are always concrete, so a clash is a clash — fail.
      sa.forEach((x) => sb.forEach((y) => {
        if (overlap(x, y)) {
          const days = x.days.filter((d) => y.days.includes(d)).join("/");
          (conflicts[A.course] ||= []).push(
            `${A.course} (${x.section_id}) overlaps ${B.course} (${y.section_id}) on ${days}, ${fmt(x.start_time)}–${fmt(x.end_time)}.`
          );
          (conflicts[B.course] ||= []).push(
            `${B.course} (${y.section_id}) overlaps ${A.course} (${x.section_id}) on ${days}, ${fmt(y.start_time)}–${fmt(y.end_time)}.`
          );
        }
      }));
    }
  }

  // ── Per-course checks ──
  let totalUnits = 0;
  const course_results = plans.map(({ course, sections }) => {
    const norm = normalizeCode(course);
    const entry = catalog[norm];
    const picked = resolved[course];
    const reasons = [];
    let status = "pass";
    const fail = (m) => { status = "fail"; reasons.push(m); };
    const warn = (m) => { if (status !== "fail") status = "warning"; reasons.push(m); };

    if (completed.has(norm)) fail(`${norm} is already completed.`);
    if (inProgress.has(norm)) warn(`${norm} is already in progress this term.`);

    const num = parseInt((course.match(/\d+/) || ["0"])[0], 10);
    if (num >= 400 && (levelOrder[classLevel] || 0) < 3)
      warn(`400+ level course while classified as ${classLevel} — confirm eligibility with your advisor.`);

    if (!entry) warn(`${course} was not found in the catalog for this term.`);

    if (entry) {
      totalUnits += entry.units || 0;

      picked.forEach((s) => {
        if (s.is_full || s.open_seats === 0)
          fail(`Section ${s.section_id} is full (${s.registered_seats}/${s.total_seats}).`);
        if (s.has_d_clearance)
          warn(`Section ${s.section_id} requires D-clearance from the department.`);
        if (s.notes) warn(`Registration restriction: ${s.notes}`);
      });

      const types = new Set(picked.map((s) => s.section_type));
      if (entry.has_lab && !types.has("labs")) fail(`${course} requires a lab section — none selected.`);
      if (entry.has_discussion && !types.has("discussions")) fail(`${course} requires a discussion section — none selected.`);

      if (entry.description && /prereq|requisite/i.test(entry.description))
        warn(`Prerequisite note (unverified): ${entry.description}`);
    }

    (conflicts[course] || []).forEach(fail);
    return { course, status, reasons };
  });

  const warnings = [];
  if (totalUnits > 18) warnings.push(`${totalUnits} units is above the recommended max of 18.`);
  if (totalUnits > 0 && totalUnits < 12) warnings.push(`${totalUnits} units is below full-time enrollment (12).`);

  const overall_status = course_results.some((c) => c.status === "fail")
    ? "invalid"
    : (warnings.length || course_results.some((c) => c.status === "warning")) ? "warning" : "valid";

  return { overall_status, course_results, summary: { total_units: totalUnits, warnings } };
}

// ─────────────────────────────────────────────────────────────
// Calendar
// ─────────────────────────────────────────────────────────────
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const DAY_START = 8 * 60;
const DAY_END = 21 * 60;
const SPAN = DAY_END - DAY_START;
// Course accent colors — chosen to stay legible on a white background,
// anchored by USC cardinal for the first course.
const PALETTE = ["#990000", "#1a7f37", "#1d4ed8", "#9a6a00", "#6f42c1", "#0e7490", "#b3006b"];

function Calendar({ blocks }) {
  const hours = [];
  for (let h = 8; h <= 21; h++) hours.push(h);

  return (
    <div style={{ border: "1px solid #dcdce0", borderRadius: 14, overflow: "hidden", background: "#fff", boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 10px 28px rgba(0,0,0,0.06)" }}>
      <div style={{ display: "grid", gridTemplateColumns: "46px repeat(5, 1fr)", background: "linear-gradient(180deg, #990000, #7d0000)" }}>
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }} />
        {DAYS.map((d) => (
          <div key={d} style={{ padding: "11px 0", textAlign: "center", fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "#ffcc00", borderBottom: "1px solid rgba(255,255,255,0.15)", borderLeft: "1px solid rgba(255,255,255,0.12)" }}>{d}</div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "46px repeat(5, 1fr)", position: "relative", height: 470 }}>
        {/* hour gutter */}
        <div style={{ position: "relative" }}>
          {hours.map((h) => (
            <div key={h} style={{ position: "absolute", top: `${((h * 60 - DAY_START) / SPAN) * 100}%`, right: 8, transform: "translateY(-50%)", fontSize: 9.5, color: "#9a9aa0", fontFamily: "'DM Mono', monospace" }}>
              {h % 12 || 12}{h < 12 ? "a" : "p"}
            </div>
          ))}
        </div>
        {DAYS.map((day) => (
          <div key={day} style={{ position: "relative", borderLeft: "1px solid #ededf0" }}>
            {hours.map((h) => (
              <div key={h} style={{ position: "absolute", top: `${((h * 60 - DAY_START) / SPAN) * 100}%`, left: 0, right: 0, borderTop: "1px solid #f2f2f4" }} />
            ))}
            {blocks.filter((b) => b.days.includes(day)).map((b) => {
              const top = ((toMin(b.start_time) - DAY_START) / SPAN) * 100;
              const height = ((toMin(b.end_time) - toMin(b.start_time)) / SPAN) * 100;
              return (
                <div key={`${b.section_id}-${day}`} title={`${b.course_name} ${b.section_id}`}
                  style={{ position: "absolute", top: `${top}%`, height: `${height}%`, left: 3, right: 3,
                    background: `${b.color}14`, borderLeft: `3px solid ${b.color}`, borderRadius: 7,
                    padding: "4px 7px", overflow: "hidden", fontSize: 10, lineHeight: 1.3, boxShadow: `0 2px 6px ${b.color}1f` }}>
                  <div style={{ fontWeight: 700, color: b.color, whiteSpace: "nowrap" }}>{b.course_name}</div>
                  <div style={{ color: "#6b6b72", whiteSpace: "nowrap" }}>{b.section_type.replace(/s$/, "")} · {b.section_id}</div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────
const STATUS = {
  fail: { bg: "#fdecea", border: "#f2b8b3", dot: "#c1121f", label: "Blocker", icon: "!" },
  warning: { bg: "#fff8e1", border: "#ffd54f", dot: "#a06a00", label: "Heads-up", icon: "!" },
  pass: { bg: "#eaf7ef", border: "#a7dcb8", dot: "#1a7f37", label: "OK", icon: "\u2713" },
};

// ─────────────────────────────────────────────────────────────
// Pyodide integration layer.
//
// On mount, tries to load Pyodide + Tanzil's validator. If it
// succeeds, all validation runs in Python (single source of truth).
// If it fails (no network, CDN down, dev environment without
// Pyodide script tag), falls back to mockValidate() with a visible
// banner so you always know which path is active.
//
// To fully enable Pyodide in your environment:
//   1. Serve the app from a local dev server (not file://)
//   2. Place validate_next_semester.py at ./validator/
//   3. Pyodide CDN loads automatically
//
// Once Pyodide is confirmed working, delete mockValidate() entirely.
// ─────────────────────────────────────────────────────────────
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const VALIDATOR_PY_URL = "./validator/validate_next_semester.py";

const BRIDGE_PY = `
import json
from dataclasses import asdict

def _bridge_validate(planned_json, stars_json, catalog_json, clearance_json):
    planned = json.loads(planned_json)
    stars = json.loads(stars_json)
    catalog = json.loads(catalog_json)
    clearance = json.loads(clearance_json)
    result = validate_next_semester(planned, stars, catalog, clearance)
    return json.dumps(asdict(result))
`;

async function loadPyodideValidator() {
  // Dynamically load the Pyodide script if not already present
  if (typeof globalThis.loadPyodide === "undefined") {
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = `${PYODIDE_CDN}pyodide.js`;
      s.onload = resolve;
      s.onerror = () => reject(new Error("Pyodide CDN script failed to load"));
      document.head.appendChild(s);
    });
  }

  const pyodide = await globalThis.loadPyodide({ indexURL: PYODIDE_CDN });

  // Fetch Tanzil's validator source
  const resp = await fetch(VALIDATOR_PY_URL);
  if (!resp.ok) throw new Error(`Fetch validator failed: ${resp.status}`);
  let src = await resp.text();

  // Strip the if __name__ == "__main__" block — it tries to read
  // fixture files from disk which don't exist in the browser.
  src = src.replace(/if\s+__name__\s*==\s*["']__main__["'][\s\S]*/, "");

  await pyodide.runPythonAsync(src);
  await pyodide.runPythonAsync(BRIDGE_PY);

  return pyodide;
}

// Mock dept_clearance data — trimmed to departments relevant to MOCK_CATALOG.
// Real file (from Tanzil's repo) has ~90 entries; this is a subset for demo
// purposes. Once static hosting is set up, fetch the real dept_clearance.json
// instead of using this constant.
const MOCK_DEPT_CLEARANCE = {
  _schema_version: "1.4",
  _lookup_logic: "Match on dept_code (course prefix) first. If no match, fall back to entries where type='school_fallback' and school matches the course's school.",
  departments: [
    {
      dept_code: "ACCT",
      dept_name: "Accounting (Leventhal School of Accounting)",
      school: "Marshall",
      clearance_required_for: "ACCT 370 and ACCT 371 are D-clearance at all times. Most other ACCT courses switch to D-clearance at the end of Week 2.",
      how_to_get_clearance: "Contact your Leventhal academic advisor or email leventhalug@marshall.usc.edu.",
      contact_email: "leventhalug@marshall.usc.edu",
      contact_office: "Leventhal School of Accounting, ACC 101",
      contact_phone: "(213) 740-4838",
      typical_turnaround: "2-3 business days",
      verified: true,
    },
    {
      dept_code: "BUCO",
      dept_name: "Business Communication (Marshall General)",
      also_covers_prefixes: ["FBE", "DSO", "MOR", "MKT"],
      school: "Marshall",
      clearance_required_for: "BUCO electives switch to D-clearance at the end of Week 1. Directed research, internships, and honors courses are D-clearance at all times.",
      how_to_get_clearance: "Email undergrad.advising@marshall.usc.edu with your full name, USC ID, USC email, course number, major, and graduating semester.",
      contact_email: "undergrad.advising@marshall.usc.edu",
      contact_office: "Jill and Frank Fertitta Hall (JFF) 201",
      contact_phone: "213-740-0690",
      typical_turnaround: "2-3 business days",
      verified: true,
    },
  ],
};

export default function App() {
  const [expanded, setExpanded] = useState([]);   // course names shown in picker
  const [picked, setPicked] = useState({});        // section_id -> {course_name, ...section}
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [validating, setValidating] = useState(false);

  // ── Real STARS upload state ──
  // starsReport starts as the demo fallback; once a student uploads a real
  // PDF, this becomes Avi's actual parsed output. Everything downstream
  // (Pyodide call, mock fallback, the STARS badge) reads from this state,
  // not a hardcoded constant.
  const [starsReport, setStarsReport] = useState(DEMO_STARS);
  const [starsSource, setStarsSource] = useState("demo"); // "demo" | "parsing" | "parsed" | "manual" | "failed"
  const [starsStatusMsg, setStarsStatusMsg] = useState("");
  const fileInputRef = useRef(null);

  const handleStarsUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStarsSource("parsing");
    setStarsStatusMsg("Reading file…");
    setResult(null);

    try {
      const parsed = await parseStarsReport(file, {
        onStatus: (msg) => setStarsStatusMsg(msg),
        onProgress: (page, total) => setStarsStatusMsg(`OCR: page ${page}/${total}`),
      });

      if (!parsed) {
        // Parser explicitly returned null — both text extraction and OCR failed.
        // Per Avi's README, this is the signal to prompt manual entry.
        setStarsSource("failed");
        setStarsStatusMsg("Couldn't read this PDF automatically. Manual entry needed.");
        return;
      }

      setStarsReport(parsed);
      setStarsSource("parsed");
      setStarsStatusMsg(`Parsed — ${parsed.classLevel}, ${parsed.completedCourses.length} completed courses.`);
    } catch (err) {
      console.error("[stars] Parse error:", err);
      setStarsSource("failed");
      setStarsStatusMsg(`Parse error: ${err.message}. Manual entry needed.`);
    }
  };

  // Pyodide state
  const [pyodideStatus, setPyodideStatus] = useState("loading"); // "loading" | "ready" | "fallback"
  const pyodideRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    loadPyodideValidator()
      .then((pyodide) => {
        if (cancelled) return;
        pyodideRef.current = pyodide;
        setPyodideStatus("ready");
        console.log("[validator] Pyodide loaded — using Python validator.");
      })
      .catch((err) => {
        if (cancelled) return;
        console.warn("[validator] Pyodide unavailable, using JS mock fallback:", err.message);
        setPyodideStatus("fallback");
      });
    return () => { cancelled = true; };
  }, []);

  const courseNames = Object.keys(MOCK_CATALOG);
  const suggestions = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toUpperCase().replace(/[\s-]/g, "");
    return courseNames.filter((c) => c.replace(/\s/g, "").includes(q) && !expanded.includes(c)).slice(0, 6);
  }, [query, expanded]);

  const colorFor = (courseName) => PALETTE[expanded.indexOf(courseName) % PALETTE.length];

  const addCourse = (c) => { setExpanded((e) => [...e, c]); setQuery(""); setResult(null); };
  const removeCourse = (c) => {
    setExpanded((e) => e.filter((x) => x !== c));
    setPicked((p) => Object.fromEntries(Object.entries(p).filter(([, s]) => s.course_name !== c)));
    setResult(null);
  };
  const toggleSection = (courseName, section) => {
    setResult(null);
    setPicked((p) => {
      const n = { ...p };
      if (n[section.section_id]) delete n[section.section_id];
      else n[section.section_id] = { ...section, course_name: courseName };
      return n;
    });
  };

  const pickedList = Object.values(picked);
  const blocks = pickedList
    .filter((s) => s.start_time && s.days?.length)
    .map((s) => ({ ...s, color: colorFor(s.course_name) }));

  // Build the section-aware payload we agreed with Tanzil:
  //   [{ course: "CSCI 104", sections: ["29903", "30119"] }]
  const payload = expanded.map((c) => ({
    course: c,
    sections: pickedList.filter((s) => s.course_name === c).map((s) => s.section_id),
  }));

  const totalUnits = expanded.reduce((sum, c) => sum + (MOCK_CATALOG[c]?.units || 0), 0);

  // Sections are required on every entry, so the GUI enforces it rather than
  // letting an invalid payload reach the validator.
  const needSections = payload.filter((p) => !p.sections.length).map((p) => p.course);
  const canValidate = expanded.length > 0 && needSections.length === 0 && !validating;

  const runValidate = async () => {
    setValidating(true);
    try {
      if (pyodideStatus === "ready" && pyodideRef.current) {
        // ── Real path: call Tanzil's Python via Pyodide ──
        const bridge = pyodideRef.current.globals.get("_bridge_validate");
        const resultJson = bridge(
          JSON.stringify(payload),
          JSON.stringify(starsReport),
          JSON.stringify(MOCK_CATALOG),
          JSON.stringify(MOCK_DEPT_CLEARANCE)
        );
        setResult(JSON.parse(resultJson));
      } else {
        // ── Fallback: JS mock (delete this once Pyodide is confirmed working) ──
        setResult(mockValidate(payload, starsReport, MOCK_CATALOG));
      }
    } catch (err) {
      console.error("[validator] Validation error:", err);
      setResult({
        overall_status: "invalid",
        course_results: [{ course: "System", status: "fail", reasons: [`Validation error: ${err.message}`] }],
        summary: { total_units: totalUnits, warnings: [] },
      });
    }
    setValidating(false);
  };

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", background: "#f4f4f5", color: "#1a1a1a", minHeight: "100vh" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700&display=swap');
        * { box-sizing: border-box; }
        .mono { font-family: 'DM Mono', monospace; }
        .serif { font-family: 'Playfair Display', Georgia, serif; }
        button { transition: background .15s ease, border-color .15s ease, color .15s ease, box-shadow .18s ease, transform .1s ease; }
        button:focus-visible { outline: 2px solid #990000; outline-offset: 2px; }
        input:focus { outline: none; border-color: #990000; box-shadow: 0 0 0 3px rgba(153,0,0,0.14); }
        .chip:hover { background: rgba(255,255,255,0.28) !important; }
        .course-card { transition: border-color .18s ease, box-shadow .18s ease; }
        .course-card:hover { border-color: #cfcfd4; box-shadow: 0 8px 22px rgba(0,0,0,0.09); }
        .suggestion:hover { background: rgba(153,0,0,0.06) !important; }
        .section-row:hover { background: #f7f7f8 !important; border-color: #e2e2e6 !important; }
        .remove-btn:hover { color: #c1121f !important; background: rgba(193,18,31,0.1) !important; }
        .validate-btn:not(:disabled):hover { box-shadow: 0 8px 22px rgba(153,0,0,0.32); transform: translateY(-1px); }
        .validate-btn:not(:disabled):active { transform: translateY(0); box-shadow: 0 3px 10px rgba(153,0,0,0.28); }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.18); border-radius: 8px; border: 2px solid transparent; background-clip: padding-box; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.3); background-clip: padding-box; }
        ::-webkit-scrollbar-track { background: transparent; }
      `}</style>

      <div style={{ borderBottom: "3px solid #ffcc00", background: "linear-gradient(180deg, #990000, #7d0000)", padding: "20px 28px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, boxShadow: "0 2px 10px rgba(0,0,0,0.15)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 42, height: 42, borderRadius: 10, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 21, fontWeight: 700, color: "#990000", background: "#ffcc00", boxShadow: "0 3px 10px rgba(0,0,0,0.25)" }}>{"✓"}</div>
          <div>
            <div className="serif" style={{ fontSize: 23, fontWeight: 700, letterSpacing: "-0.01em", color: "#fff", lineHeight: 1.1 }}>Next Semester Validator</div>
            <div style={{ fontSize: 12.5, color: "rgba(255,255,255,0.82)", marginTop: 3 }}>Pick your sections for Fall 2026, then check the schedule before you register.</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 9, alignItems: "center" }}>
          <input ref={fileInputRef} type="file" accept="application/pdf" onChange={handleStarsUpload} style={{ display: "none" }} />
          <button onClick={() => fileInputRef.current?.click()}
            className="mono chip"
            style={{ fontSize: 11.5, color: starsSource === "parsed" ? "#eafaef" : starsSource === "failed" ? "#ffdede" : "#fff",
              background: "rgba(255,255,255,0.16)", border: "1px solid rgba(255,255,255,0.35)", borderRadius: 8, padding: "6px 12px", cursor: "pointer", fontFamily: "inherit" }}>
            {starsSource === "parsing" ? (starsStatusMsg || "Parsing…")
              : starsSource === "parsed" ? `✓ STARS uploaded · ${starsReport.classLevel} · ${starsReport.completedCourses.length} completed`
              : starsSource === "failed" ? "⚠ Parse failed — click to retry"
              : `STARS · ${starsReport.classLevel} (demo) · ${starsReport.completedCourses.length} completed · click to upload real PDF`}
          </button>
          <div className="mono" style={{ fontSize: 10, display: "flex", alignItems: "center", gap: 5, color: "#fff",
            background: "rgba(255,255,255,0.16)", border: "1px solid rgba(255,255,255,0.35)", borderRadius: 8, padding: "6px 10px" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: pyodideStatus === "ready" ? "#6ee7a0" : pyodideStatus === "loading" ? "#ffcc00" : "#ffcc00", boxShadow: "0 0 6px currentColor" }} />
            {pyodideStatus === "ready" ? "Python" : pyodideStatus === "loading" ? "Loading Pyodide…" : "JS mock"}
          </div>
        </div>
      </div>

      {starsSource === "failed" && (
        <div style={{ margin: "16px 28px 0", padding: "12px 16px", background: "#fdecea", border: "1px solid #f2b8b3", borderLeft: "4px solid #c1121f", borderRadius: 8, fontSize: 12.5, color: "#4a1210" }}>
          Couldn't read that STARS PDF automatically (tried direct text extraction and OCR). Per Avi's parser, this means manual entry is needed —
          that flow isn't built in this GUI yet, so demo data is being used for now. Try a different PDF, or continue with the click above.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(340px, 430px) 1fr", gap: 24, padding: 28, alignItems: "start" }}>

        {/* LEFT — pick courses + sections */}
        <div>
          <div style={{ position: "relative", marginBottom: 18 }}>
            <input value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Add a course — try CSCI 104, ACCT 370, BUAD 494…"
              style={{ width: "100%", background: "#fff", border: "1px solid #d3d3d8", borderRadius: 10, padding: "12px 15px", color: "#1a1a1a", fontSize: 13.5, fontFamily: "inherit", transition: "border-color .15s ease, box-shadow .15s ease" }} />
            {suggestions.length > 0 && (
              <div style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "#fff", border: "1px solid #d3d3d8", borderRadius: 10, marginTop: 6, zIndex: 20, overflow: "hidden", boxShadow: "0 14px 34px rgba(0,0,0,0.16)" }}>
                {suggestions.map((c) => (
                  <button key={c} onClick={() => addCourse(c)} className="suggestion"
                    style={{ display: "flex", justifyContent: "space-between", width: "100%", textAlign: "left", padding: "10px 14px", border: "none", borderBottom: "1px solid #eeeef0", background: "transparent", color: "#1a1a1a", cursor: "pointer", fontFamily: "inherit", fontSize: 13 }}>
                    <span><b>{c}</b> <span style={{ color: "#7a7a80" }}>{MOCK_CATALOG[c].units} units</span></span>
                    <span style={{ color: "#990000", fontWeight: 700 }}>+</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {expanded.length === 0 && (
            <div style={{ color: "#7a7a80", fontSize: 13, padding: "32px 20px", textAlign: "center", border: "1px dashed #cfcfd4", borderRadius: 12, background: "#fafafb" }}>
              <div style={{ fontSize: 22, marginBottom: 6, opacity: 0.55 }}>🔍</div>
              No courses yet. Search above to start building.
            </div>
          )}

          {expanded.map((courseName) => {
            const entry = MOCK_CATALOG[courseName];
            const color = colorFor(courseName);
            return (
              <div key={courseName} className="course-card" style={{ border: "1px solid #e2e2e6", borderRadius: 12, marginBottom: 13, overflow: "hidden", background: "#fff", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>
                <div style={{ padding: "12px 15px", background: "#f6f6f7", borderBottom: "1px solid #eaeaee", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, borderLeft: `4px solid ${color}` }}>
                  <div>
                    <span style={{ fontWeight: 700, fontSize: 14, color: "#1a1a1a" }}>{courseName}</span>
                    <span style={{ color: "#7a7a80", fontSize: 12, marginLeft: 8 }}>{entry.units} units</span>
                  </div>
                  <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                    {entry.has_d_clearance && <Tag c="#a06a00">D-clear</Tag>}
                    {entry.has_restrictions && <Tag c="#6f42c1">Restricted</Tag>}
                    {entry.has_lab && <Tag c="#1a7f37">Lab req</Tag>}
                    {entry.has_discussion && <Tag c="#1a7f37">Disc req</Tag>}
                    <button onClick={() => removeCourse(courseName)} className="remove-btn" style={{ background: "none", border: "none", color: "#9a9aa0", cursor: "pointer", fontSize: 16, padding: "1px 5px", borderRadius: 6, lineHeight: 1 }}>×</button>
                  </div>
                </div>
                <div style={{ padding: "6px 9px 9px" }}>
                  {Object.entries(entry.sections).map(([group, secs]) => (
                    <div key={group}>
                      <div style={{ fontSize: 9.5, textTransform: "uppercase", letterSpacing: "0.08em", color: "#9a9aa0", padding: "8px 5px 4px", fontWeight: 700 }}>{group}</div>
                      {secs.map((s) => {
                        const on = !!picked[s.section_id];
                        return (
                          <button key={s.section_id} onClick={() => toggleSection(courseName, s)}
                            className={on ? undefined : "section-row"}
                            style={{ width: "100%", textAlign: "left", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8,
                              background: on ? `${color}14` : "transparent", border: `1px solid ${on ? color + "80" : "#ededf0"}`,
                              borderRadius: 9, padding: "8px 10px", margin: "3px 0", color: "#1a1a1a", fontFamily: "inherit" }}>
                            <span style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                              <span className="mono" style={{ fontSize: 11, color: on ? color : "#9a9aa0", width: 44, flexShrink: 0, fontWeight: 500 }}>{s.section_id}</span>
                              <span className="mono" style={{ fontSize: 11.5, color: "#6b6b72", whiteSpace: "nowrap" }}>
                                {s.days.join("/")} {fmt(s.start_time)}–{fmt(s.end_time)}
                              </span>
                            </span>
                            <span style={{ display: "flex", alignItems: "center", gap: 9, flexShrink: 0 }}>
                              {s.has_d_clearance && <span style={{ fontSize: 9.5, color: "#a06a00", fontWeight: 700, border: "1px solid #ffd54f", background: "#fff8e1", borderRadius: 4, padding: "1px 4px" }}>D</span>}
                              <span style={{ fontSize: 11, fontWeight: 600, color: s.is_full ? "#c1121f" : "#1a7f37" }}>{s.is_full ? "Full" : `${s.open_seats} open`}</span>
                              <span style={{ fontSize: 14, color: on ? color : "#c2c2c8", lineHeight: 1 }}>{on ? "✓" : "+"}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* RIGHT — calendar + validate + results */}
        <div style={{ position: "sticky", top: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <span className="serif" style={{ fontSize: 18, fontWeight: 700, color: "#990000" }}>Your week</span>
            <span className="mono" style={{ fontSize: 12, color: totalUnits > 18 ? "#c1121f" : "#5a5a60", background: "#fff", border: "1px solid #e2e2e6", borderRadius: 20, padding: "4px 11px" }}>{totalUnits} units · {pickedList.length} sections</span>
          </div>

          <Calendar blocks={blocks} />

          <button onClick={runValidate} disabled={!canValidate} className="validate-btn"
            style={{ width: "100%", marginTop: 16, padding: "13px", borderRadius: 10, border: "none",
              cursor: canValidate ? "pointer" : "not-allowed",
              background: canValidate ? "linear-gradient(135deg, #b3131a, #990000)" : "#e6e6e9",
              color: canValidate ? "#fff" : "#a0a0a6", fontWeight: 700, fontSize: 14, fontFamily: "inherit",
              boxShadow: canValidate ? "0 4px 14px rgba(153,0,0,0.26)" : "none", letterSpacing: "0.01em" }}>
            {validating ? "Validating…" : "Validate schedule"}
          </button>
          {needSections.length > 0 && (
            <div style={{ marginTop: 9, fontSize: 12, color: "#7a7a80", textAlign: "center" }}>
              Pick at least one section for {needSections.join(", ")} to validate.
            </div>
          )}

          {result && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14, padding: "13px 15px", borderRadius: 12,
                background: result.overall_status === "valid" ? "#eaf7ef" : result.overall_status === "warning" ? "#fff8e1" : "#fdecea",
                border: `1px solid ${result.overall_status === "valid" ? "#a7dcb8" : result.overall_status === "warning" ? "#ffd54f" : "#f2b8b3"}`,
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)" }}>
                <span style={{ width: 30, height: 30, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#fff", flexShrink: 0,
                  background: result.overall_status === "valid" ? "#1a7f37" : result.overall_status === "warning" ? "#a06a00" : "#c1121f",
                  boxShadow: `0 2px 8px ${result.overall_status === "valid" ? "rgba(26,127,55,0.4)" : result.overall_status === "warning" ? "rgba(160,106,0,0.4)" : "rgba(193,18,31,0.4)"}` }}>
                  {result.overall_status === "valid" ? "\u2713" : "!"}
                </span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14.5, color: "#1a1a1a" }}>
                    {result.overall_status === "valid" ? "Schedule looks good" : result.overall_status === "warning" ? "Worth reviewing" : "Schedule has problems"}
                  </div>
                  <div className="mono" style={{ fontSize: 11.5, color: "#5a5a60", marginTop: 2 }}>
                    {result.summary.total_units} units{result.summary.warnings.map((w, i) => <span key={i}> · {w}</span>)}
                  </div>
                </div>
              </div>

              {result.course_results.map((cr, i) => {
                const s = STATUS[cr.status];
                return (
                  <div key={i} style={{ background: s.bg, border: `1px solid ${s.border}`, borderRadius: 10, padding: "11px 13px", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                      <span style={{ width: 18, height: 18, borderRadius: "50%", background: s.dot, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "#fff", flexShrink: 0 }}>{s.icon}</span>
                      <span style={{ fontWeight: 700, fontSize: 13.5, color: "#1a1a1a" }}>{cr.course}</span>
                      <span style={{ fontSize: 10.5, fontWeight: 700, color: s.dot, marginLeft: "auto", textTransform: "uppercase", letterSpacing: "0.04em" }}>{s.label}</span>
                    </div>
                    {cr.reasons.map((r, j) => (
                      <div key={j} style={{ fontSize: 12.5, color: "#44444a", lineHeight: 1.5, paddingLeft: 27, marginTop: 4 }}>{r}</div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Tag({ children, c }) {
  return <span style={{ fontSize: 9.5, color: c, border: `1px solid ${c}4d`, background: `${c}1f`, borderRadius: 6, padding: "2px 7px", fontWeight: 600, letterSpacing: "0.01em", whiteSpace: "nowrap" }}>{children}</span>;
}
