/* Constellation STARS parser v0.1 (POC). Pure functions, no network. */
(function (root) {
  const TERM = { '1': 'Spring', '2': 'Summer', '3': 'Fall' };
  const FLAGS = {
    IP: 'In progress', FF: 'Freshman forgiveness (not in GPA)', EX: 'Excess credit',
    OS: 'Out of sequence (no credit)', D: 'Credit deleted, counts in GPA',
    Z: 'Credit deleted, not in GPA', R: 'Repeatable course', P: 'Taken pass/no pass'
  };
  const SUFFIX = { G: 'GE course', L: 'Has a lab', X: 'Credit restriction', M: 'Diversity',
    P: 'Traditions and historical foundations', W: 'Citizenship in a global era' };
  const GRADE = { TR: 'Transfer', RG: 'In progress', CR: 'Credit', IN: 'Incomplete',
    IX: 'Expired incomplete', MG: 'Missing grade', NS: 'Not submitted' };
  const EXC = { RE: 'Substitution', RA: 'Alternative', CW: 'Course waived', UW: 'Units waived', RW: 'Requirement waived' };
  const ACRONYMS = new Set(['USC', 'GE', 'GESM', 'GPA', 'AP', 'AI', 'II', 'I', 'P/NP', 'BS', 'BA', 'IP', 'III', 'IV']);

  const COURSE_RE = /^(\d{5})\s+(TRNSFR WORK|AP\d{2}:COMP|[A-Z]{2,4} {0,3}\d{3}[A-Z]?)\s+(?:([GLXMPW]{1,3}(?: [GLXMPW]{1,2})?)\s+)?(\d+\.\d)\s+(?:([A-Z]{1,2}[+-]?|Lp)\s+)?(>(?:IP|FF|EX|OS|D|Z|R|P))?\s*(.*)$/;
  const CODE_RE = /[A-Z]{2,4} {0,3}\d{3}[A-Z]?/g;
  const SUB_RE = /^(IP[+-]|[+-]R?)?\s*(\d+|OR)\)\s+(.*)$/;
  const LOOSE_SUB_RE = /^(IP[+-]|[+-]R?)\s+([A-Z].{8,})$/;
  const BLOCK_RE = /^(NO|OK|IP)\s+(.+)$/;

  function termName(code) {
    if (!/^\d{5}$/.test(code) || code.startsWith('9999')) return '';
    return `${TERM[code[4]] || 'Term'} ${code.slice(0, 4)}`;
  }

  function sentence(raw) {
    const words = raw.replace(/\s+/g, ' ').trim().replace(/:$/, '').split(' ');
    let out = words.map((w, i) => {
      const bare = w.replace(/[^A-Z0-9/]/g, '');
      if (/^[A-Z]{2,5}\d{2,3}[A-Z]?$/.test(bare) || ACRONYMS.has(bare) || /^GE-[A-Z]$/.test(w)) return w;
      const lw = w.toLowerCase();
      return i === 0 ? lw.charAt(0).toUpperCase() + lw.slice(1) : lw;
    }).join(' ');
    out = out.replace(/\bcategory ([a-h])\b/gi, (_, l) => `Category ${l.toUpperCase()}`)
      .replace(/\(must be taken at usc\)/i, '(must be taken at USC)')
      .replace(/"c"/i, '"C"')
      .replace(/\s+(requirement\s+)?(has been|has not been) (met|satisfied)\.?$/i, '').replace(/\s+requirement met\.?$/i, '')
      .replace(/\.$/, '')
      .replace(/(: | - )([a-z])/g, (_, s, c) => s + c.toUpperCase());
    return out;
  }

  function normCode(code) {
    const m = code.match(/^([A-Z]{2,4}) *(\d{3}[A-Z]?)$/);
    return m ? `${m[1]} ${m[2]}` : code;
  }

  function parseCourse(line) {
    const m = line.match(COURSE_RE);
    if (!m) return null;
    const [, term, code, suffix, units, gradeRaw, flag, title] = m;
    const grade = !gradeRaw ? '' : gradeRaw === 'Lp' ? 'hidden' : gradeRaw;
    const t = title.trim();
    return {
      term, termName: termName(term), code: normCode(code), suffix: (suffix || '').replace(/ /g, ''),
      units: parseFloat(units), grade, flag: flag ? flag.slice(1) : '',
      title: t.length >= 29 && !/^AP /.test(t) ? t + '…' : t,
      truncated: t.length >= 29,
      isAP: /^AP\d/.test(code), display: /^AP\d/.test(code) ? t.replace(/^AP /, 'AP ').toLowerCase().replace(/\b(\w)/g, x => x.toUpperCase()).replace(/^Ap /, 'AP ').replace(/\bU\.s\./, 'U.S.').replace(/\bBc\b/, 'BC').replace(/\bEngl\b/, 'English').replace(/\bSci\b/, 'Science') : normCode(code), isTransferTotal: code === 'TRNSFR WORK'
    };
  }

  // ---------- redaction ----------
  function redact(text) {
    const lines = text.replace(/\r/g, '').replace(/\f/g, '\n').split('\n');
    const out = []; let skip = false; const removed = new Set();
    for (const line of lines) {
      if (/USC Diploma Information/i.test(line)) { skip = true; removed.add('diploma name'); removed.add('mailing address'); continue; }
      if (skip) { if (/^\s*={10,}/.test(line)) { skip = false; out.push(line); } continue; }
      if (/STARS Report for|ID#/i.test(line)) { removed.add('name'); removed.add('student ID'); continue; }
      if (/^\s*\d{1,2}\/\d{1,2}\/\d{2},\s+\d{1,2}:\d{2}\s*[AP]M\b/.test(line) || /^\s*X{15,}.*\d+\/\d+\s*$/.test(line) || /^\s*(Lp|X{3,}(\s+X{3,})*)\s*$/.test(line)) continue;
      let l = line.replace(/^\s*Lp\s+(?=\S)/, '').replace(/^\s*X\.XXX\s+(?=[A-Z])/, '');
      if (/\b\d{10}\b/.test(l)) { l = l.replace(/\b\d{10}\b/g, '[redacted]'); removed.add('student ID'); }
      out.push(l);
    }
    return { text: out.join('\n'), removed: [...removed] };
  }

  // ---------- main parse ----------
  function parse(input) {
    const { text, removed } = redact(input);
    let lines = text.split('\n').map(l => l.replace(/\s+$/, ''));
    const start = lines.findIndex(l => /PREPARED:|STARS - DEGREE PROGRESS REPORT/.test(l));
    if (start < 0) throw new Error('This file doesn\'t look like a STARS report. Open your report in OASIS, click Print Report, and save it as a PDF.');
    const endIdx = lines.findIndex(l => /END OF ANALYSIS/.test(l));
    lines = lines.slice(start, endIdx > 0 ? endIdx : undefined).map(l => l.trim()).filter(Boolean);

    const R = { meta: {}, blocks: [], notes: [], redacted: removed, courses: new Map(), overallIncomplete: false };
    const full = lines.join('\n');
    const g = (re) => { const m = full.match(re); return m ? m[1].trim() : ''; };
    R.meta.prepared = g(/PREPARED:\s*(.+)/);
    R.meta.program = g(/PROGRAM:\s*(\d+)/);
    R.meta.catalogYear = g(/CATALOG YEAR:\s*(\d{5})/);
    const di = lines.findIndex(l => /STARS - DEGREE PROGRESS REPORT/.test(l));
    if (di >= 0) { R.meta.degree = (lines[di + 1] || '').toLowerCase().replace(/\b(\w)/g, c => c.toUpperCase()).replace(/\bOf\b/, 'of'); R.meta.major = sentence(lines[di + 2] || '').replace(/\b(\w)/g, c => c.toUpperCase()).replace(/\bFor\b/g, 'for').replace(/\bAi\b/, 'AI'); }
    R.meta.entrance = g(/Term of USC Entrance\s+(\d{5})/);
    R.meta.classLevel = g(/Current Class Level\s+(\w+)/);
    R.meta.gradDate = g(/Expected Graduation Date\s*-\s*(.+)/);
    R.meta.minor = g(/MINOR:\s*(.+)/);
    const sem = full.match(/YOU HAVE ([A-Z]+) REMAINING\s+SEMESTERS?/);
    if (sem) R.meta.semestersLeft = sem[1].toLowerCase();
    R.overallIncomplete = /AT LEAST ONE REQUIREMENT HAS NOT BEEN SATISFIED/.test(full);

    // split into chunks by underscore rules
    const chunks = []; let cur = [];
    for (const l of lines) {
      if (/^_{10,}$/.test(l)) { if (cur.length) chunks.push(cur); cur = []; } else cur.push(l);
    }
    if (cur.length) chunks.push(cur);

    for (const chunk of chunks) {
      const head = chunk[0];
      if (/^CURRENT REGISTRATION:/.test(head)) { chunk.forEach(l => addCourse(R, parseCourse(l), 'Current registration')); continue; }
      if (/^OTHER COURSES IN YOUR/.test(head)) { chunk.forEach(l => addCourse(R, parseCourse(l), null)); continue; }
      if (/^NO MORE THAN|^PLEASE NOTE|LEGEND|INTERNAL|^\*{3}|The Degree Progress|PERTINENT DATA|PREPARED/.test(head)) {
        if (/^PLEASE NOTE THE FOLLOWING GENERAL EDUCATION/.test(head)) R.notes.push({ kind: 'ge-rules', lines: chunk.slice(1) });
        if (/^NO MORE THAN/.test(head)) { R.notes.push({ kind: 'unit-limits', lines: chunk.filter(l => !parseCourse(l)) }); chunk.forEach(l => addCourse(R, parseCourse(l), null)); }
        continue;
      }
      const bm = head.match(BLOCK_RE);
      if (!bm) continue;
      R.blocks.push(parseBlock(chunk, R));
    }
    R.courseList = [...R.courses.values()].filter(c => !c.isTransferTotal)
      .sort((a, b) => a.term.localeCompare(b.term) || a.code.localeCompare(b.code));
    delete R.courses;
    R.left = whatsLeft(R);
    R.units = R.blocks.find(b => b.kind === 'units') || null;
    R.gpa = (R.blocks.find(b => b.kind === 'gpa-overall') || {}).earned || '';
    R.majorGpa = (R.blocks.find(b => b.kind === 'gpa-major') || {}).earned || '';
    return R;
  }

  function addCourse(R, c, countsToward) {
    if (!c) return;
    const key = c.term + c.code;
    if (!R.courses.has(key)) R.courses.set(key, { ...c, countsToward: [] });
    const e = R.courses.get(key);
    if (countsToward && !e.countsToward.includes(countsToward)) e.countsToward.push(countsToward);
  }

  const STOP = /^(EARNED:|IN-PROCESS:|-->|NEEDS:|NOTE|\*\*|SELECT FROM:|IN-P\b|\d+ COURSES? TAKEN|IP$)/;
  function readTitle(chunk, i, first) {
    let title = first, j = i + 1;
    while (j < chunk.length && !/[:.]$/.test(title) && j - i < 6) {
      const n = chunk[j];
      if (STOP.test(n) || COURSE_RE.test(n) || SUB_RE.test(n)) break;
      title += ' ' + n; j++;
    }
    return { title: title.replace(/\s+/g, ' '), next: j };
  }

  function classify(t) {
    const rules = [
      [/MINIMUM OF (\d+) UNITS IS REQUIRED FOR DEGREE/, m => ['units', `Total units`, 'University']],
      [/(\d+)-UNIT RESIDENCY|MINIMUM OF (\d+) UNDERGRADUATE UNITS MUST (?:BE )?COMPLETED AT USC/, m => ['residency', `Residency: ${m[1] || m[2]} units taken at USC`, 'University']],
      [/(\d+)-UNIT UPPER DIVISION|MINIMUM OF (\d+) UPPER DIVISION UNITS/, m => ['upper', `Upper-division units: ${m[1] || m[2]} required`, 'University']],
      [/CUMULATIVE GPA REQUIRED OF ALL USC/, () => ['gpa-overall', 'Overall GPA: 2.0 minimum', 'University']],
      [/GPA REQUIRED IN ALL UPPER DIVISION/, () => ['gpa-major', 'Major upper-division GPA: 2.0 minimum', 'University']],
      [/LIMIT OF (\d+) UPPER DIVISION UNITS IN ANY ONE DEPARTMENT/, m => ['cap', `Limit: ${m[1]} upper-division units per department`, 'University']],
      [/MINIMUM OF (\d+) UNITS APPLICABLE TO THE DEGREE MUST BE\s+EARNED IN THE COLLEGE/, m => ['college', `Dornsife units: ${m[1]} required`, 'University']],
      [/COMPOSITION\/WRITING/, () => ['writing', 'Writing', 'Writing and language']],
      [/FOREIGN LANGUAGE/, () => ['language', 'Foreign language', 'Writing and language']],
      [/CORE LITERACIES/, () => ['ge-core', 'Core Literacies (8 courses, 6 categories)', 'General education']],
      [/THEMATIC OPTION/, () => ['ge-to', 'Thematic Option', 'General education']],
      [/GLOBAL PERSPECTIVES REQUIREMENT/, () => ['ge-global', 'Global Perspectives (categories G and H)', 'General education']],
      [/^MATH REQUIREMENT/, () => ['math', 'Math', 'School and major']],
      [/ACCOUNTING REQUIREMENT/, () => ['accounting', 'Accounting', 'School and major']],
      [/^MAJOR REQUIREMENTS FOR [A-Z ,&]+?(?: MAJORS)?\s*(?:--\s*(.+?))?\s*(?:\(|:|$)/, m => ['major', m[1] ? `Major: ${sentence(m[1]).toLowerCase()}` : 'Major requirements', 'School and major']],
      [/^(.+?) REQUIREMENTS? FOR [A-Z ]+/, m => ['major-other', sentence(m[1]) + ' requirements', 'School and major']],
      [/DEPARTMENT MAJOR UPPER DIVISION/, () => ['major-upper', 'Major upper-division units', 'School and major']],
    ];
    for (const [re, f] of rules) { const m = t.match(re); if (m) return f(m); }
    return ['other', sentence(t.replace(/\s*\(.*$/, '')), 'Other'];
  }

  const STATUS = { OK: 'done', NO: 'needs', IP: 'progress', '+': 'done', '-': 'needs', 'IP-': 'progress', 'IP+': 'progress' };

  function parseBlock(chunk, R) {
    const [, st, rest] = chunk[0].match(BLOCK_RE);
    const { title, next } = readTitle(chunk, 0, rest);
    const [kind, name, group] = classify(title);
    const b = { kind, name, group, status: STATUS[st], raw: title, subs: [], courses: [], notes: [] };
    let sub = null;
    for (let i = next; i < chunk.length; i++) {
      const l = chunk[i];
      const sm = l.match(SUB_RE) || (!/^\+\s+NO MORE THAN/.test(l) && l.match(LOOSE_SUB_RE) && [null, l.match(LOOSE_SUB_RE)[1], '', l.match(LOOSE_SUB_RE)[2]]);
      if (sm) {
        const rt = readTitle(chunk, i, sm[3]);
        const isAlt = sm[2] === 'OR';
        const st = sm[1] ? STATUS[sm[1].replace(/R$/, '')] : null;
        sub = { status: st, alt: isAlt, name: sentence(rt.title), raw: rt.title, courses: [], notes: [], taken: 0, inProgress: 0 };
        if (isAlt && b.subs.length) { b.subs[b.subs.length - 1].orAlt = sub; } else b.subs.push(sub);
        i = rt.next - 1; continue;
      }
      if (/^IP[+-]?$/.test(l)) continue;
      if (/^\+\s+NO MORE THAN/.test(l)) continue;
      const c = parseCourse(l);
      const tgt = sub || b;
      if (c) {
        tgt.courses.push(c);
        const label = sub ? `${b.name}: ${shortSub(sub.name)}` : b.name;
        if (kind !== 'units') addCourse(R, c, label); else addCourse(R, c, null);
        continue;
      }
      let m;
      if (/^(-->\s*NEEDS|EARNED):\s*(X\.XXX\s*)?GPA/.test(l)) { tgt.gpaHidden = true; continue; }
      if ((m = l.match(/^EARNED:\s*([\d.]+)\s*(\w[\w-]*)?/))) { tgt.earned = m[1]; tgt.earnedUnit = (m[2] || '').toLowerCase(); continue; }
      if ((m = l.match(/^IN-PROCESS:\s*([\d.]+)/))) { tgt.inProcess = m[1]; continue; }
      if ((m = l.match(/NEEDS:\s*([\d.]+)\s*([A-Z-]+)/))) { tgt.needs = m[1]; tgt.needsUnit = m[2].toLowerCase(); continue; }
      if ((m = l.match(/^SELECT FROM:\s*(.+)$/))) {
        let sf = m[1].trim();
        while (i + 1 < chunk.length && /^([A-Z]{2,4} {0,3}\d{3}[A-Z]?|OR|TO)(\s+([A-Z]{2,4} {0,3}\d{3}[A-Z]?|OR|TO))*$/.test(chunk[i + 1])) sf += ' ' + chunk[++i];
        tgt.selectFrom = selectList(sf); continue; }
      if ((m = l.match(/^IN-P\s*-+>\s*(?:[\d.]+\s+UNITS\s+)?(\d+)\s+COURSE/))) { tgt.inProgress = +m[1]; continue; }
      if (/^IN-P\s*-+>/.test(l) || /UNITS EARNED/.test(l)) continue;
      if ((m = l.match(/^(\d+) COURSES? TAKEN/))) { tgt.taken = +m[1]; continue; }
      if ((m = l.match(/^NOTE:\s*(RE|RA|CW|UW|RW)\s*-\s*(.+)$/))) {
        const n = `${EXC[m[1]]}: ${m[2].replace(/COURSE WAIVED\s*/i, '').replace(/SUB\s+/i, '').replace(/([A-Z]{2,4}) ?(\d{3})/g, '$1 $2').replace(/ FOR /, ' in place of ')}`;
        if (!tgt.notes.includes(n)) tgt.notes.push(n); continue;
      }
    }
    for (const s of b.subs) if (!s.status) s.status = s.needs ? 'needs' : (s.courses.length ? 'done' : 'needs');
    return b;
  }

  function selectList(sf) {
    const ge = sf.match(/CATEGORY (GE-[A-Z])/);
    if (ge) return [`Any ${ge[1]} course`];
    if (/^\*+/.test(sf)) return [];
    const toks = sf.replace(/([A-Z]{2,4}) {0,3}(\d{3}[A-Z]?)/g, '$1 $2').split(/\s{1,}(?=[A-Z]{2,4} \d|OR\b|TO\b)|(?<=\b(?:OR|TO))\s+/).map(s => s.trim()).filter(Boolean);
    const out = [];
    for (let k = 0; k < toks.length; k++) {
      const t = toks[k];
      if ((t === 'OR' || t === 'TO') && out.length && toks[k + 1]) {
        const nxt = toks[++k];
        out[out.length - 1] += t === 'OR' ? ` or ${nxt}` : ` to ${nxt.replace(/^[A-Z]+ /, '')}`;
      } else if (!out.includes(t)) out.push(t);
    }
    return out;
  }

  function shortSub(n) {
    const s = n.replace(/^Complete (one|two|three) (courses? )?from /i, '').replace(/\s+requirement(\s*\(.*\))?$/i, '').replace(/:$/, '');
    return /^the following$/i.test(s) ? 'choose from the list' : s;
  }

  function whatsLeft(R) {
    const out = [];
    for (const b of R.blocks) {
      if (b.status === 'done' || b.kind === 'cap' || /gpa/.test(b.kind)) continue;
      if (b.kind === 'units' && b.needs) {
        const total = (b.raw.match(/MINIMUM OF (\d+)/) || [])[1];
        out.push({ area: 'University', count: fmt(b.needs), unit: 'units', label: `Toward the ${total} unit total`,
          detail: b.inProcess ? `Assumes your ${fmt(b.inProcess)} in-progress units pass.` : '', status: 'needs', options: [] });
        continue;
      }
      if (!b.subs.length) {
        if (b.status === 'needs' && b.needs) out.push({ area: b.group === 'University' ? 'University' : b.name, count: fmt(b.needs), unit: b.needsUnit, label: b.name,
          detail: b.inProcess ? `Assumes your ${fmt(b.inProcess)} in-progress units pass.` : '', status: 'needs', options: [] });
        continue;
      }
      const area = b.kind === 'major' ? 'Major' : b.name.replace(/ \(.*\)$/, '');
      const open = b.subs.filter(s => s.status === 'needs');
      const groupNeed = /sub-group/.test(b.needsUnit || '') ? +b.needs : 0;
      if (groupNeed && open.length > groupNeed) {
        out.push({ area, count: String(groupNeed), unit: groupNeed === 1 ? 'category' : 'categories', label: `Pick ${groupNeed} of these ${open.length}`,
          status: 'needs', options: open.map(s => shortSub(s.name)), detail: 'STARS lets you choose which ones.' });
        b.subs.filter(s => s.status === 'progress' && s.needs).forEach(s => out.push(leftRow(area, s)));
        continue;
      }
      for (const s of b.subs) {
        if (s.status === 'done') continue;
        if (!s.needs && !(s.status === 'needs' && (s.selectFrom || []).length)) continue;
        out.push(leftRow(area, s));
      }
    }
    return out;
  }
  function leftRow(area, s) {
    const n = s.needs ? +s.needs : 0; let label = shortSub(s.name), detail = '';
    if (label === 'choose from the list') label = 'Elective choice';
    label = label.charAt(0).toUpperCase() + label.slice(1);
    if (label.length > 58) { const m = label.match(/^(.{12,58}?)(?:\s+\(|,\s+|\s+-\s+)(.+)$/); if (m) { label = m[1]; detail = m[2].replace(/\)$/, ''); detail = detail.charAt(0).toUpperCase() + detail.slice(1) + '.'; } }
    const unit = !n ? 'see list' : /course|set/.test(s.needsUnit) ? (n === 1 ? 'course' : 'courses') : s.needsUnit;
    let options = s.selectFrom || [];
    if (!options.length) { const c = s.name.match(/Category ([A-H])\b/); if (c) options = [`Any GE-${c[1]} course`]; }
    if (s.orAlt) options = options.concat((s.orAlt.selectFrom || []).map(o => `or ${o}`));
    if (s.inProgress) detail = (detail ? detail + ' ' : '') + `${s.inProgress} more in progress now.`;
    return { area, count: n ? fmt(n) : '', unit, label, status: s.status, options, detail };
  }
  function fmt(n) { return String(parseFloat(n)); }

  const api = { parse, redact, parseCourse, termName, FLAGS, SUFFIX, GRADE };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.StarsParser = api;
})(typeof window !== 'undefined' ? window : globalThis);
