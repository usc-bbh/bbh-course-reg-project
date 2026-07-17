import React, { useState, useMemo } from "react";

// ─────────────────────────────────────────────────────────────
// MOCK COURSE CATALOG — shaped like bbh_schedule_data_v4.json
// In production, load the real v4 JSON.
// ─────────────────────────────────────────────────────────────
const MOCK_CATALOG = {
  "CSCI 104": {
    course_name: "CSCI 104", units: 4, description: "Data structures and OOP. Prerequisite: CSCI 103.",
    has_lab: true, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "29903", mode: "Lecture", instructor: "Mark Redekopp", days: ["Mon", "Wed"], start_time: "10:00", end_time: "11:20", open_seats: 12, is_full: false, has_d_clearance: false, notes: null },
      ],
      labs: [
        { section_id: "30119", mode: "Lab", instructor: "TBD", days: ["Fri"], start_time: "10:00", end_time: "11:50", open_seats: 5, is_full: false, has_d_clearance: false, notes: null },
        { section_id: "29905", mode: "Lab", instructor: "TBD", days: ["Fri"], start_time: "14:00", end_time: "15:50", open_seats: 0, is_full: true, has_d_clearance: false, notes: null },
      ],
    },
  },
  "CSCI 170": {
    course_name: "CSCI 170", units: 4, description: "Discrete methods in CS. Prerequisite: CSCI 103.",
    has_lab: false, has_discussion: true, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "30121", mode: "Lecture", instructor: "Aaron Cote", days: ["Tue", "Thu"], start_time: "11:00", end_time: "12:20", open_seats: 3, is_full: false, has_d_clearance: false, notes: null },
      ],
      discussions: [
        { section_id: "29929", mode: "Discussion", instructor: "TBD", days: ["Fri"], start_time: "09:00", end_time: "09:50", open_seats: 8, is_full: false, has_d_clearance: false, notes: null },
      ],
    },
  },
  "MATH 226": {
    course_name: "MATH 226", units: 4, description: "Calculus III. Prerequisite: MATH 126.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "39100", mode: "Lecture", instructor: "Nemanja Kosovalic", days: ["Mon", "Wed"], start_time: "10:00", end_time: "11:20", open_seats: 20, is_full: false, has_d_clearance: false, notes: null },
        { section_id: "39101", mode: "Lecture", instructor: "TBD", days: ["Tue", "Thu"], start_time: "14:00", end_time: "15:20", open_seats: 15, is_full: false, has_d_clearance: false, notes: null },
      ],
    },
  },
  "ACCT 370": {
    course_name: "ACCT 370", units: 4, description: "Decision-making and problem solving for accounting professionals.",
    has_lab: false, has_discussion: false, has_d_clearance: true, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "14025", mode: "Lecture", instructor: "Taylor Wiesen", days: ["Tue", "Thu"], start_time: "14:00", end_time: "15:50", open_seats: 0, is_full: true, has_d_clearance: true, notes: null },
        { section_id: "14027", mode: "Lecture", instructor: "Taylor Wiesen", days: ["Tue", "Thu"], start_time: "18:00", end_time: "19:50", open_seats: 34, is_full: false, has_d_clearance: true, notes: null },
      ],
    },
  },
  "BUAD 494": {
    course_name: "BUAD 494", units: 2, description: "Senior research and thesis.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: true,
    sections: {
      lectures: [
        { section_id: "15124", mode: "Lecture", instructor: "Sriram Dasu", days: ["Mon"], start_time: "17:00", end_time: "18:50", open_seats: 12, is_full: false, has_d_clearance: false, notes: "Section 15124 is for Honors Research and Thesis offered by the Data Sciences and Operations Department." },
      ],
    },
  },
  "BUAD 311": {
    course_name: "BUAD 311", units: 4, description: "Operations management.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "14911", mode: "Lecture", instructor: "TBD", days: ["Mon", "Wed"], start_time: "08:00", end_time: "09:20", open_seats: 10, is_full: false, has_d_clearance: false, notes: null },
        { section_id: "14913", mode: "Lecture", instructor: "TBD", days: ["Mon", "Wed"], start_time: "12:00", end_time: "13:20", open_seats: 5, is_full: false, has_d_clearance: false, notes: null },
      ],
    },
  },
  "WRIT 340": {
    course_name: "WRIT 340", units: 4, description: "Advanced writing.",
    has_lab: false, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "60100", mode: "Lecture", instructor: "TBD", days: ["Tue", "Thu"], start_time: "09:30", end_time: "10:50", open_seats: 2, is_full: false, has_d_clearance: false, notes: null },
      ],
    },
  },
  "CSCI 103": {
    course_name: "CSCI 103", units: 4, description: "Intro to programming in C/C++.",
    has_lab: true, has_discussion: false, has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "30211", mode: "Lecture", instructor: "TBD", days: ["Tue", "Thu"], start_time: "11:00", end_time: "12:20", open_seats: 44, is_full: false, has_d_clearance: false, notes: null },
      ],
      labs: [
        { section_id: "30212", mode: "Lab", instructor: "TBD", days: ["Wed"], start_time: "12:00", end_time: "12:50", open_seats: 18, is_full: false, has_d_clearance: false, notes: null },
      ],
    },
  },
};

// Mock STARS report (Avi's parser output shape)
const MOCK_STARS = {
  completedCourses: [
    { code: "CSCI103", grade: "A" },
    { code: "MATH225", grade: "B+" },
    { code: "WRIT150", grade: "A-" },
  ],
  inProgressCourses: [],
  classLevel: "Junior",
};

// ─────────────────────────────────────────────────────────────
// Normalize: "CSCI103" → "CSCI 103", "csci 103" → "CSCI 103"
// ─────────────────────────────────────────────────────────────
function normalizeCode(code) {
  const m = code.trim().match(/^([A-Za-z]+)\s*(\d+[A-Za-z]?)$/);
  if (!m) return code.trim().toUpperCase();
  return `${m[1].toUpperCase()} ${m[2].toUpperCase()}`;
}

// ─────────────────────────────────────────────────────────────
// Mock validator — mirrors Tanzil's validate_next_semester()
// Input:  planned_courses (list of course code strings)
//         stars_report (Avi's parser output)
//         course_catalog (keyed by normalized course code)
// Output: { overall_status, course_results, summary }
// ─────────────────────────────────────────────────────────────
function toMinutes(t) {
  if (!t || t === "TBA") return null;
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

function allSections(entry) {
  if (!entry || !entry.sections) return [];
  return Object.values(entry.sections).flat().filter((s) => !s.is_cancelled);
}

function sectionTimeOptions(entry) {
  return allSections(entry)
    .map((s) => ({ days: new Set(s.days || []), start: toMinutes(s.start_time), end: toMinutes(s.end_time) }))
    .filter((o) => o.days.size > 0 && o.start !== null && o.end !== null);
}

function sectionsOverlap(a, b) {
  const sharedDay = [...a.days].some((d) => b.days.has(d));
  return sharedDay && a.start < b.end && b.start < a.end;
}

function mockValidate(plannedCourses, starsReport, catalog) {
  const completed = new Set((starsReport.completedCourses || []).map((c) => normalizeCode(c.code)));
  const inProgress = new Set((starsReport.inProgressCourses || []).map((c) => normalizeCode(c.code)));
  const classLevel = starsReport.classLevel || "";
  const levelOrder = { Freshman: 1, Sophomore: 2, Junior: 3, Senior: 4 };

  // Time conflicts (all pairs)
  const timeConflicts = {};
  const optionsByC = {};
  plannedCourses.forEach((c) => { optionsByC[c] = sectionTimeOptions(catalog[normalizeCode(c)]); });
  for (let i = 0; i < plannedCourses.length; i++) {
    const a = plannedCourses[i], optsA = optionsByC[a];
    if (!optsA.length) continue;
    for (let j = i + 1; j < plannedCourses.length; j++) {
      const b = plannedCourses[j], optsB = optionsByC[b];
      if (!optsB.length) continue;
      if (optsA.every((oa) => optsB.every((ob) => sectionsOverlap(oa, ob)))) {
        (timeConflicts[a] ||= []).push(`${a} has no section that avoids conflicting with ${b}.`);
        (timeConflicts[b] ||= []).push(`${b} has no section that avoids conflicting with ${a}.`);
      }
    }
  }

  let totalUnits = 0;
  const courseResults = plannedCourses.map((course) => {
    const norm = normalizeCode(course);
    const entry = catalog[norm];
    const reasons = [];
    let status = "pass";
    const fail = (msg) => { status = "fail"; reasons.push(msg); };
    const warn = (msg) => { if (status !== "fail") status = "warning"; reasons.push(msg); };

    // Already taken
    if (completed.has(norm)) fail(`${norm} is already completed.`);
    if (inProgress.has(norm)) warn(`${norm} is already in progress this term.`);

    // Standing
    const num = parseInt((course.match(/\d+/) || ["0"])[0], 10);
    if (num >= 400 && (levelOrder[classLevel] || 0) < 3)
      fail(`${classLevel}s are not eligible for 400+ level courses.`);

    // Not in catalog
    if (!entry) { warn(`${course} was not found in the course catalog for this term.`); }

    if (entry) {
      totalUnits += entry.units || 0;

      // D-clearance
      if (entry.has_d_clearance) warn(`${course} requires departmental clearance (D-clearance) to enroll.`);

      // Prereq note
      if (entry.description && /prereq|requisite/i.test(entry.description))
        warn(`Prerequisite note (unverified): ${entry.description}`);

      // Seat availability
      const secs = allSections(entry);
      if (secs.length && secs.every((s) => s.is_full))
        fail(`Every section of ${course} is full for this term.`);

      // Lab/discussion pairing
      const components = [];
      if (entry.has_lab) components.push("lab");
      if (entry.has_discussion) components.push("discussion");
      if (components.length)
        warn(`${course} requires a linked ${components.join("/")} section — register for a matching section.`);

      // Major restrictions
      if (entry.has_restrictions) {
        const notes = [...new Set(allSections(entry).filter((s) => s.notes).map((s) => s.notes))];
        notes.forEach((n) => warn(`Registration restriction: ${n}`));
        if (!notes.length) warn(`${course} has registration restrictions — check section notes on WebReg.`);
      }
    }

    // Time conflicts
    if (timeConflicts[course]) timeConflicts[course].forEach(fail);

    return { course, status, reasons };
  });

  const summaryWarnings = [];
  if (totalUnits > 18) summaryWarnings.push(`Planned load is ${totalUnits} units, above the recommended max of 18.`);

  let overall;
  if (courseResults.some((c) => c.status === "fail")) overall = "invalid";
  else if (summaryWarnings.length || courseResults.some((c) => c.status === "warning")) overall = "warning";
  else overall = "valid";

  return { overall_status: overall, course_results: courseResults, summary: { total_units: totalUnits, warnings: summaryWarnings } };
}

// ─────────────────────────────────────────────────────────────
// UI Components
// ─────────────────────────────────────────────────────────────
const STATUS_STYLE = {
  fail: { bg: "#3a1518", border: "#7f1d1d", dot: "#ef4444", label: "Blocker", icon: "!" },
  warning: { bg: "#3a2f12", border: "#854d0e", dot: "#f59e0b", label: "Heads-up", icon: "!" },
  pass: { bg: "#0d2818", border: "#166534", dot: "#22c55e", label: "Looks good", icon: "\u2713" },
};

function CoursePill({ name, onRemove }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#21262d", border: "1px solid #30363d", borderRadius: 20, padding: "5px 12px", fontSize: 13, fontWeight: 500 }}>
      {name}
      <button onClick={onRemove} style={{ background: "none", border: "none", color: "#7d8590", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 0 }}>{"\u00d7"}</button>
    </span>
  );
}

function CourseResultCard({ result }) {
  const s = STATUS_STYLE[result.status];
  return (
    <div style={{ background: s.bg, border: `1px solid ${s.border}`, borderRadius: 10, padding: "12px 14px", marginBottom: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: result.reasons.length ? 6 : 0 }}>
        <span style={{ width: 20, height: 20, borderRadius: "50%", background: s.dot, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#fff", flexShrink: 0 }}>{s.icon}</span>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{result.course}</span>
        <span style={{ fontSize: 12, color: s.dot, marginLeft: "auto" }}>{s.label}</span>
      </div>
      {result.reasons.map((r, i) => (
        <div key={i} style={{ fontSize: 13, color: "#b1bac4", lineHeight: 1.5, paddingLeft: 28, marginTop: 2 }}>{r}</div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// App
// ─────────────────────────────────────────────────────────────
export default function App() {
  const [planned, setPlanned] = useState([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);

  const courseList = Object.keys(MOCK_CATALOG);
  const suggestions = useMemo(() => {
    if (!query.trim()) return [];
    const norm = query.toUpperCase().replace(/\s+/g, "");
    return courseList.filter((c) => {
      const compacted = c.replace(/\s+/g, "");
      return compacted.includes(norm) && !planned.includes(c);
    }).slice(0, 6);
  }, [query, planned]);

  const addCourse = (course) => { setPlanned((p) => [...p, course]); setQuery(""); setResult(null); };
  const removeCourse = (course) => { setPlanned((p) => p.filter((c) => c !== course)); setResult(null); };
  const runValidation = () => setResult(mockValidate(planned, MOCK_STARS, MOCK_CATALOG));

  const totalUnits = planned.reduce((sum, c) => sum + (MOCK_CATALOG[c]?.units || 0), 0);

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", background: "#0d1117", color: "#e6edf3", minHeight: "100vh" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        .mono { font-family: 'DM Mono', monospace; }
        button:focus-visible { outline: 2px solid #58a6ff; outline-offset: 2px; }
      `}</style>

      {/* Header */}
      <div style={{ borderBottom: "1px solid #21262d", padding: "20px 28px", display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.02em" }}>Next semester validator</div>
          <div style={{ fontSize: 13, color: "#7d8590", marginTop: 2 }}>Add courses you plan to take, then validate your schedule.</div>
        </div>
        <div className="mono" style={{ fontSize: 12, color: "#7d8590", background: "#161b22", border: "1px solid #21262d", borderRadius: 6, padding: "4px 10px" }}>
          STARS: {MOCK_STARS.classLevel} · {MOCK_STARS.completedCourses.length} courses completed
        </div>
      </div>

      <div style={{ maxWidth: 640, margin: "0 auto", padding: "24px 28px" }}>

        {/* Search + add courses */}
        <div style={{ position: "relative", marginBottom: 20 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search courses (e.g. CSCI 104, MATH 226)..."
            style={{ width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 14, fontFamily: "inherit" }}
          />
          {suggestions.length > 0 && (
            <div style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "#161b22", border: "1px solid #30363d", borderRadius: 8, marginTop: 4, overflow: "hidden", zIndex: 10 }}>
              {suggestions.map((c) => {
                const entry = MOCK_CATALOG[c];
                return (
                  <button key={c} onClick={() => addCourse(c)}
                    style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%", textAlign: "left", padding: "10px 14px", border: "none", borderBottom: "1px solid #21262d", background: "transparent", color: "#e6edf3", cursor: "pointer", fontFamily: "inherit", fontSize: 13 }}>
                    <span>
                      <span style={{ fontWeight: 600 }}>{c}</span>
                      <span style={{ color: "#7d8590", marginLeft: 8 }}>{entry.units} units</span>
                      {entry.has_d_clearance && <span style={{ color: "#f59e0b", marginLeft: 8, fontSize: 11 }}>D-clearance</span>}
                      {entry.has_restrictions && <span style={{ color: "#a371f7", marginLeft: 8, fontSize: 11 }}>Restricted</span>}
                    </span>
                    <span style={{ color: "#3fb950", fontSize: 18 }}>+</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Planned courses */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>Planned courses</span>
            <span className="mono" style={{ fontSize: 12, color: totalUnits > 18 ? "#f85149" : "#7d8590" }}>
              {totalUnits} units
            </span>
          </div>
          {planned.length === 0 ? (
            <div style={{ color: "#7d8590", fontSize: 13, padding: "16px 0" }}>No courses added yet. Search above to build your schedule.</div>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {planned.map((c) => <CoursePill key={c} name={c} onRemove={() => removeCourse(c)} />)}
            </div>
          )}
        </div>

        {/* Validate button */}
        <button onClick={runValidation} disabled={planned.length === 0}
          style={{ width: "100%", padding: "12px", borderRadius: 8, border: "none",
            cursor: planned.length ? "pointer" : "not-allowed",
            background: planned.length ? "#238636" : "#21262d",
            color: planned.length ? "#fff" : "#484f58",
            fontWeight: 600, fontSize: 14, fontFamily: "inherit", marginBottom: 20 }}>
          Validate schedule
        </button>

        {/* Results */}
        {result && (
          <div>
            {/* Overall status */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, padding: "12px 14px",
              background: result.overall_status === "valid" ? "#0d2818" : result.overall_status === "warning" ? "#3a2f12" : "#3a1518",
              border: `1px solid ${result.overall_status === "valid" ? "#166534" : result.overall_status === "warning" ? "#854d0e" : "#7f1d1d"}`,
              borderRadius: 10 }}>
              <span style={{ width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#fff",
                background: result.overall_status === "valid" ? "#22c55e" : result.overall_status === "warning" ? "#f59e0b" : "#ef4444" }}>
                {result.overall_status === "valid" ? "\u2713" : "!"}
              </span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>
                  {result.overall_status === "valid" ? "Schedule looks good" : result.overall_status === "warning" ? "Schedule has warnings" : "Schedule has problems"}
                </div>
                <div className="mono" style={{ fontSize: 12, color: "#7d8590", marginTop: 2 }}>
                  {result.summary.total_units} units planned
                  {result.summary.warnings.map((w, i) => <span key={i}> · {w}</span>)}
                </div>
              </div>
            </div>

            {/* Per-course results */}
            {result.course_results.map((cr, i) => <CourseResultCard key={i} result={cr} />)}
          </div>
        )}
      </div>
    </div>
  );
}
