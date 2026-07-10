import React, { useState, useMemo } from "react";

// ─────────────────────────────────────────────────────────────
// MOCK DATA — shaped like bbh_schedule_data_v4.json (terms_data → courses → sections)
// In production this is replaced by loading the real v4 JSON.
// ─────────────────────────────────────────────────────────────
const MOCK_COURSES = [
  {
    course_name: "CSCI 104", units: "4.0", has_lab: true, has_discussion: false,
    has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "29903", mode: "Lecture", instructor: "Mark Redekopp", days: ["Mon", "Wed"], start_time: "10:00", end_time: "11:20", open_seats: 12, is_full: false, has_d_clearance: false, notes: null, section_type: "lectures" },
      ],
      labs: [
        { section_id: "30119", mode: "Lab", instructor: "TBD", days: ["Fri"], start_time: "10:00", end_time: "11:50", open_seats: 5, is_full: false, has_d_clearance: false, notes: null, section_type: "labs" },
        { section_id: "29905", mode: "Lab", instructor: "TBD", days: ["Fri"], start_time: "14:00", end_time: "15:50", open_seats: 0, is_full: true, has_d_clearance: false, notes: null, section_type: "labs" },
      ],
    },
  },
  {
    course_name: "CSCI 170", units: "4.0", has_lab: false, has_discussion: true,
    has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "30121", mode: "Lecture", instructor: "Aaron Cote", days: ["Tue", "Thu"], start_time: "11:00", end_time: "12:20", open_seats: 3, is_full: false, has_d_clearance: false, notes: null, section_type: "lectures" },
      ],
      discussions: [
        { section_id: "29929", mode: "Discussion", instructor: "TBD", days: ["Fri"], start_time: "09:00", end_time: "09:50", open_seats: 8, is_full: false, has_d_clearance: false, notes: null, section_type: "discussions" },
      ],
    },
  },
  {
    course_name: "MATH 226", units: "4.0", has_lab: false, has_discussion: false,
    has_d_clearance: false, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "39100", mode: "Lecture", instructor: "Nemanja Kosovalic", days: ["Mon", "Wed"], start_time: "10:00", end_time: "11:20", open_seats: 20, is_full: false, has_d_clearance: false, notes: null, section_type: "lectures" },
      ],
    },
  },
  {
    course_name: "ACCT 370", units: "4.0", has_lab: false, has_discussion: false,
    has_d_clearance: true, has_restrictions: false,
    sections: {
      lectures: [
        { section_id: "14025", mode: "Lecture", instructor: "Taylor Wiesen", days: ["Tue", "Thu"], start_time: "14:00", end_time: "15:50", open_seats: 0, is_full: true, has_d_clearance: true, notes: null, section_type: "lectures" },
        { section_id: "14027", mode: "Lecture", instructor: "Taylor Wiesen", days: ["Tue", "Thu"], start_time: "18:00", end_time: "19:50", open_seats: 34, is_full: false, has_d_clearance: true, notes: null, section_type: "lectures" },
      ],
    },
  },
  {
    course_name: "BUAD 494", units: "2.0", has_lab: false, has_discussion: false,
    has_d_clearance: false, has_restrictions: true,
    sections: {
      lectures: [
        { section_id: "15124", mode: "Lecture", instructor: "Sriram Dasu", days: ["Mon"], start_time: "17:00", end_time: "18:50", open_seats: 12, is_full: false, has_d_clearance: false, notes: "Section 15124 is for Honors Research and Thesis offered by the Data Sciences and Operations Department.", section_type: "lectures" },
      ],
    },
  },
];

// Mock STARS report (Avi's parser shape: camelCase, no-space codes)
const MOCK_STARS = {
  completedCourses: ["CSCI103", "MATH225", "WRIT150"],
  classLevel: "Junior",
};

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────
const normalizeCode = (code) => code.replace(/([A-Z]+)\s*(\d+.*)/i, "$1 $2").toUpperCase().trim();

const timeToMin = (t) => {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
};

const daysOverlap = (a, b) => a.some((d) => b.includes(d));

// ─────────────────────────────────────────────────────────────
// MOCK validator — stands in for Tanzil's function until it's ready.
// Same input/output contract we agreed on: { proposed_sections, completed_courses } → { status, flags }
// ─────────────────────────────────────────────────────────────
function mockValidate(selectedSections, starsReport) {
  const flags = [];
  const completed = new Set((starsReport.completedCourses || []).map(normalizeCode));

  // Seat availability
  for (const s of selectedSections) {
    if (s.is_full || s.open_seats === 0) {
      flags.push({ check: "seat_availability", severity: "error", message: `${s.course_name} (${s.section_id}) is full — no open seats.` });
    }
  }

  // Time conflicts (all pairs)
  for (let i = 0; i < selectedSections.length; i++) {
    for (let j = i + 1; j < selectedSections.length; j++) {
      const a = selectedSections[i], b = selectedSections[j];
      if (daysOverlap(a.days, b.days) && timeToMin(a.start_time) < timeToMin(b.end_time) && timeToMin(b.start_time) < timeToMin(a.end_time)) {
        flags.push({ check: "time_conflict", severity: "error", message: `${a.course_name} (${a.section_id}) conflicts with ${b.course_name} (${b.section_id}) on ${a.days.filter((d) => b.days.includes(d)).join("/")}.` });
      }
    }
  }

  // Lab / discussion pairing
  const byCourse = {};
  selectedSections.forEach((s) => { (byCourse[s.course_name] ||= []).push(s); });
  for (const [courseName, secs] of Object.entries(byCourse)) {
    const course = MOCK_COURSES.find((c) => c.course_name === courseName);
    if (!course) continue;
    const types = new Set(secs.map((s) => s.section_type));
    if (course.has_lab && !types.has("labs"))
      flags.push({ check: "component_pairing", severity: "error", message: `${courseName} requires a lab section — none selected.` });
    if (course.has_discussion && !types.has("discussions"))
      flags.push({ check: "component_pairing", severity: "error", message: `${courseName} requires a discussion section — none selected.` });
  }

  // D-clearance (warning)
  for (const s of selectedSections) {
    if (s.has_d_clearance)
      flags.push({ check: "d_clearance", severity: "warning", message: `${s.course_name} (${s.section_id}) requires D-clearance from the department before you can register.` });
  }

  // Restriction notes (warning)
  for (const s of selectedSections) {
    if (s.notes)
      flags.push({ check: "restriction", severity: "warning", message: `${s.course_name} (${s.section_id}): ${s.notes}` });
  }

  // Prereq — stub (Francis's catalogue data not wired yet)
  flags.push({ check: "prerequisites", severity: "info", message: "Prerequisite checks are pending catalogue data — not yet verified." });

  const hasError = flags.some((f) => f.severity === "error");
  return { status: hasError ? "flagged" : (flags.some((f) => f.severity === "warning") ? "flagged" : "ok"), flags };
}

// ─────────────────────────────────────────────────────────────
// UI
// ─────────────────────────────────────────────────────────────
const SEV = {
  error: { bg: "#3a1518", border: "#7f1d1d", dot: "#ef4444", label: "Blocker" },
  warning: { bg: "#3a2f12", border: "#854d0e", dot: "#f59e0b", label: "Heads-up" },
  info: { bg: "#132a33", border: "#155e63", dot: "#22d3ee", label: "Note" },
};

export default function App() {
  const [selected, setSelected] = useState({}); // section_id → section (with course_name)
  const [result, setResult] = useState(null);
  const [query, setQuery] = useState("");

  const toggle = (course, section) => {
    setResult(null);
    setSelected((prev) => {
      const next = { ...prev };
      if (next[section.section_id]) delete next[section.section_id];
      else next[section.section_id] = { ...section, course_name: course.course_name, units: course.units };
      return next;
    });
  };

  const selectedList = Object.values(selected);
  const totalUnits = selectedList.reduce((sum, s) => sum + parseFloat(s.units || 0), 0);

  const filtered = useMemo(() => {
    if (!query.trim()) return MOCK_COURSES;
    return MOCK_COURSES.filter((c) => c.course_name.toLowerCase().includes(query.toLowerCase()));
  }, [query]);

  const runValidate = () => setResult(mockValidate(selectedList, MOCK_STARS));

  return (
    <div style={{ fontFamily: "'DM Sans', system-ui, sans-serif", background: "#0d1117", color: "#e6edf3", minHeight: "100vh", padding: "0" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        .mono { font-family: 'DM Mono', monospace; }
        button:focus-visible { outline: 2px solid #58a6ff; outline-offset: 2px; }
      `}</style>

      {/* Header */}
      <div style={{ borderBottom: "1px solid #21262d", padding: "20px 28px", display: "flex", alignItems: "baseline", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.02em" }}>Next Semester Validator</div>
          <div style={{ fontSize: 13, color: "#7d8590", marginTop: 2 }}>Build your Fall 2026 schedule, then check it before you register.</div>
        </div>
        <div className="mono" style={{ fontSize: 12, color: "#7d8590", background: "#161b22", border: "1px solid #21262d", borderRadius: 6, padding: "4px 10px" }}>
          STARS: {MOCK_STARS.classLevel} · {MOCK_STARS.completedCourses.length} courses done
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 0, alignItems: "start" }}>
        {/* LEFT — course catalogue */}
        <div style={{ padding: "20px 28px" }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search courses (e.g. CSCI 104)…"
            style={{ width: "100%", background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 14, marginBottom: 18, fontFamily: "inherit" }}
          />
          {filtered.map((course) => (
            <div key={course.course_name} style={{ marginBottom: 18, border: "1px solid #21262d", borderRadius: 10, overflow: "hidden", background: "#0f141a" }}>
              <div style={{ padding: "12px 16px", background: "#161b22", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{course.course_name}
                  <span style={{ color: "#7d8590", fontWeight: 400, marginLeft: 8, fontSize: 13 }}>{course.units} units</span>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  {course.has_d_clearance && <Tag color="#f59e0b">D-clearance</Tag>}
                  {course.has_restrictions && <Tag color="#a371f7">Restricted</Tag>}
                  {course.has_lab && <Tag color="#3fb950">Lab</Tag>}
                  {course.has_discussion && <Tag color="#3fb950">Discussion</Tag>}
                </div>
              </div>
              <div style={{ padding: "6px 10px" }}>
                {Object.values(course.sections).flat().map((section) => {
                  const on = !!selected[section.section_id];
                  return (
                    <button key={section.section_id} onClick={() => toggle(course, section)}
                      style={{ width: "100%", textAlign: "left", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
                        background: on ? "#132a1a" : "transparent", border: on ? "1px solid #2ea043" : "1px solid transparent", borderRadius: 8, padding: "9px 12px", margin: "3px 0", color: "#e6edf3", fontFamily: "inherit" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span className="mono" style={{ fontSize: 12, color: on ? "#3fb950" : "#7d8590", width: 52 }}>{section.section_id}</span>
                        <span style={{ fontSize: 13, textTransform: "capitalize", color: "#adbac7", width: 78 }}>{section.section_type.replace(/s$/, "")}</span>
                        <span className="mono" style={{ fontSize: 12, color: "#7d8590" }}>{section.days.join("/")} {section.start_time}–{section.end_time}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={{ fontSize: 12, color: section.is_full ? "#f85149" : "#3fb950" }}>{section.is_full ? "Full" : `${section.open_seats} open`}</span>
                        <span style={{ fontSize: 18, color: on ? "#3fb950" : "#484f58", lineHeight: 1 }}>{on ? "✓" : "+"}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* RIGHT — cart + validate */}
        <div style={{ padding: "20px 28px 20px 0", position: "sticky", top: 20 }}>
          <div style={{ border: "1px solid #21262d", borderRadius: 12, background: "#0f141a", overflow: "hidden" }}>
            <div style={{ padding: "14px 16px", borderBottom: "1px solid #21262d", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>Your schedule</span>
              <span className="mono" style={{ fontSize: 12, color: totalUnits > 18 ? "#f85149" : "#7d8590" }}>{totalUnits} units</span>
            </div>
            <div style={{ padding: selectedList.length ? "8px 10px" : "24px 16px" }}>
              {selectedList.length === 0 ? (
                <div style={{ color: "#7d8590", fontSize: 13, textAlign: "center" }}>No sections yet. Add some from the catalogue to get started.</div>
              ) : selectedList.map((s) => (
                <div key={s.section_id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 8px", fontSize: 13 }}>
                  <span><span style={{ fontWeight: 500 }}>{s.course_name}</span> <span className="mono" style={{ color: "#7d8590", fontSize: 11 }}>{s.section_id}</span></span>
                  <button onClick={() => toggle({ course_name: s.course_name }, s)} style={{ background: "none", border: "none", color: "#7d8590", cursor: "pointer", fontSize: 16 }}>×</button>
                </div>
              ))}
            </div>
            <div style={{ padding: 12, borderTop: "1px solid #21262d" }}>
              <button onClick={runValidate} disabled={selectedList.length === 0}
                style={{ width: "100%", padding: "11px", borderRadius: 8, border: "none", cursor: selectedList.length ? "pointer" : "not-allowed",
                  background: selectedList.length ? "#238636" : "#21262d", color: selectedList.length ? "#fff" : "#484f58", fontWeight: 600, fontSize: 14, fontFamily: "inherit" }}>
                Validate schedule
              </button>
            </div>
          </div>

          {/* Results */}
          {result && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: result.status === "ok" ? "#3fb950" : "#f59e0b" }} />
                <span style={{ fontWeight: 600, fontSize: 14 }}>{result.status === "ok" ? "Looks good" : "Some things to review"}</span>
              </div>
              {result.flags.map((f, i) => {
                const sev = SEV[f.severity];
                return (
                  <div key={i} style={{ background: sev.bg, border: `1px solid ${sev.border}`, borderRadius: 8, padding: "10px 12px", marginBottom: 8, display: "flex", gap: 10 }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: sev.dot, marginTop: 6, flexShrink: 0 }} />
                    <div>
                      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", color: sev.dot, fontWeight: 600, marginBottom: 2 }}>{sev.label}</div>
                      <div style={{ fontSize: 13, color: "#e6edf3", lineHeight: 1.4 }}>{f.message}</div>
                    </div>
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

function Tag({ children, color }) {
  return <span style={{ fontSize: 11, color, border: `1px solid ${color}44`, background: `${color}18`, borderRadius: 5, padding: "2px 7px", fontWeight: 500 }}>{children}</span>;
}
