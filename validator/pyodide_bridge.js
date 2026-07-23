/**
 * pyodide_bridge.js
 *
 * Loads Pyodide (Python-in-the-browser via WebAssembly), fetches
 * Tanzil's validate_next_semester.py, and exposes a single async
 * function the React GUI can call:
 *
 *   const result = await validateSchedule(plannedCourses, starsReport, catalog, deptClearance);
 *
 * Returns the same { overall_status, course_results, summary } shape
 * documented in validator/README.md.
 *
 * This file replaces mockValidate() — once loaded, the JS duplicate
 * of the validation logic is gone and the Python is the single source
 * of truth, running entirely in the student's browser.
 */

// ─── Configuration ──────────────────────────────────────────
// Adjust these paths to match your deployment.
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const VALIDATOR_PY_URL = "./validator/validate_next_semester.py";

// ─── State ──────────────────────────────────────────────────
let pyodideInstance = null;
let pyodideReady = false;
let loadError = null;

// ─── Thin Python wrapper ────────────────────────────────────
// This runs inside Pyodide. It:
//   1. Imports the validator module (already exec'd into the namespace)
//   2. Defines a JSON-in/JSON-out bridge function the JS side calls
//   3. Converts the dataclass result to a plain dict for JSON serialization
const BRIDGE_PY = `
import json
from dataclasses import asdict

def _bridge_validate(planned_json, stars_json, catalog_json, clearance_json):
    """
    JS calls this with four JSON strings.
    Returns a JSON string of the validation result.
    """
    planned = json.loads(planned_json)
    stars = json.loads(stars_json)
    catalog = json.loads(catalog_json)
    clearance = json.loads(clearance_json)

    result = validate_next_semester(planned, stars, catalog, clearance)
    return json.dumps(asdict(result))
`;

// ─── Public API ─────────────────────────────────────────────

/**
 * Initialize Pyodide and load the validator. Call once on app mount.
 * Resolves when ready; rejects with an error message on failure.
 * Safe to call multiple times — subsequent calls return immediately.
 */
export async function initPyodide() {
  if (pyodideReady) return;
  if (loadError) throw new Error(loadError);

  try {
    // 1. Load Pyodide runtime
    // loadPyodide is a global provided by the Pyodide CDN script.
    // The CDN script must be loaded before this module runs —
    // add <script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"></script>
    // to your HTML, or dynamically inject it (see loadPyodideScript below).
    if (typeof globalThis.loadPyodide === "undefined") {
      await loadPyodideScript();
    }

    pyodideInstance = await globalThis.loadPyodide({
      indexURL: PYODIDE_CDN,
    });

    // 2. Fetch Tanzil's validator source
    const response = await fetch(VALIDATOR_PY_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch validator: ${response.status} ${response.statusText}`);
    }
    const validatorSource = await response.text();

    // 3. Execute the validator module in Pyodide's Python namespace.
    //    This defines validate_next_semester and all its helpers.
    //    We strip the `if __name__ == "__main__"` block so it doesn't
    //    try to read fixture files from a nonexistent filesystem.
    const cleanedSource = validatorSource.replace(
      /if\s+__name__\s*==\s*["']__main__["'][\s\S]*/,
      ""
    );
    await pyodideInstance.runPythonAsync(cleanedSource);

    // 4. Execute the bridge wrapper
    await pyodideInstance.runPythonAsync(BRIDGE_PY);

    pyodideReady = true;
    console.log("[pyodide_bridge] Validator loaded and ready.");
  } catch (err) {
    loadError = `Pyodide init failed: ${err.message}`;
    console.error("[pyodide_bridge]", loadError);
    throw new Error(loadError);
  }
}

/**
 * Call the validator. Returns the parsed result object directly.
 *
 * @param {Array} plannedCourses - [{course: "CSCI 104", sections: ["29903", "30119"]}]
 * @param {Object} starsReport   - Avi's parser output (completedCourses, inProgressCourses, classLevel)
 * @param {Object} courseCatalog - Dict keyed by normalized course code, entries per catalog/README.md
 * @param {Object} deptClearance - Contents of dept_clearance.json
 * @returns {Object} { overall_status, course_results: [{course, status, reasons}], summary }
 */
export async function validateSchedule(plannedCourses, starsReport, courseCatalog, deptClearance) {
  if (!pyodideReady) {
    throw new Error("Pyodide not initialized. Call initPyodide() first.");
  }

  const bridge = pyodideInstance.globals.get("_bridge_validate");

  const resultJson = bridge(
    JSON.stringify(plannedCourses),
    JSON.stringify(starsReport),
    JSON.stringify(courseCatalog),
    JSON.stringify(deptClearance)
  );

  return JSON.parse(resultJson);
}

/**
 * Check if Pyodide is loaded and ready.
 */
export function isReady() {
  return pyodideReady;
}

/**
 * Get any load error message, or null if no error.
 */
export function getLoadError() {
  return loadError;
}

// ─── Internal: dynamic script loader ────────────────────────
function loadPyodideScript() {
  return new Promise((resolve, reject) => {
    if (typeof globalThis.loadPyodide !== "undefined") {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = `${PYODIDE_CDN}pyodide.js`;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Failed to load Pyodide script from CDN"));
    document.head.appendChild(script);
  });
}
