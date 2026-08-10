# USC Department (D-)Clearance Dataset — Documentation

Documents what's in [`dept_clearance.json`](dept_clearance.json): a 74-department dataset of undergraduate D-clearance information for PlanSC Module 4B, and where each entry's information came from.

- **Schema version:** 1.4
- **Last updated:** 2026-08-10
- **Scope:** Undergraduate D-clearance only (graduate processes out of scope)
- **Lookup logic:** Match on `dept_code` (course prefix) first; if no match, fall back to `type: "school_fallback"` entries where `school` matches the course's school

## What is a "D-clearance"?

A department-level enrollment restriction on certain USC course sections (denoted by a `D` suffix on the 5-digit section number in Schedule of Classes/WebReg) that requires student-specific permission from the offering department before the student can register on Web Registration. It is distinct from prerequisite waivers, and clearance does not guarantee an open seat.

## Data provenance

Per the file's `_notes` field: **all entries were sourced from official USC department/school advising pages.** Each entry carries its own `source_url` (the page the entry was scraped/compiled from) and a `verified` boolean indicating whether contact details and process steps were manually confirmed against the live page at compile time. The file explicitly warns that advising processes change every semester and should be cross-checked before production use.

Of the 74 entries, **70 are marked `verified: true`** and **4 are marked `verified: false`** (unverified): `PORT`, `HP`, `BKPH`, `OT` — see the "Unverified entries" section below for details.

## Entries by school

### Viterbi School of Engineering — source hub: [viterbiundergrad.usc.edu](https://viterbiundergrad.usc.edu/viterbi-undergraduate-advising/) / [myviterbi.usc.edu](http://myviterbi.usc.edu)

| Dept Code | Name | Source URL | Verified |
|---|---|---|---|
| CSCI | Computer Science | cs.usc.edu/students/d-clearance/ | ✅ |
| EE (+ECE) | Electrical & Computer Engineering | minghsiehece.usc.edu/students/ | ✅ |
| BME | Biomedical Engineering | bme.usc.edu/student-resources/undergraduate-student-resources/ | ✅ |
| AME | Aerospace & Mechanical Engineering | ame.usc.edu/current-students/ | ✅ |
| CIVL (+CEE) | Civil & Environmental Engineering | cee.usc.edu/current-students/ | ✅ |
| ISE | Industrial & Systems Engineering | ise.usc.edu/current-students/ | ✅ |
| ASTE | Astronautical Engineering | astronautics.usc.edu/ | ✅ |
| CHEE | Chemical Engineering (Mork Family) | che.usc.edu/current-students/ | ✅ |
| MASC | Materials Science (Mork Family) | chems.usc.edu/undergraduate-advising/ | ✅ |
| ENE | Energy Resources Engineering | viterbiundergrad.usc.edu/viterbi-undergraduate-advising/ | ✅ |
| ENGR | General Engineering | viterbiundergrad.usc.edu/viterbi-undergraduate-advising/ | ✅ |
| PRE-E | Pre-Engineering / Pre-CS | cs.usc.edu/students/d-clearance/ | ✅ |

Key process notes: most Viterbi departments route through the **myViterbi D-Clearance Request Manager** (myviterbi.usc.edu). CSCI is the exception — it uses a Microsoft Form for non-CSCI-major applicants, distributed by the student's home department.

### Marshall School of Business — source hub: [students.marshall.usc.edu](https://students.marshall.usc.edu/current-students/academic-advising/forms-and-other-resources/registration-information-interest-lists)

| Dept Code | Name | Source URL | Verified |
|---|---|---|---|
| BUAD (+BAEP, BUCO, FBE, DSO, MOR, MKT) | Business Administration (Marshall General) | students.marshall.usc.edu/.../registration-information-interest-lists | ✅ |
| ACCT | Accounting (Leventhal) | students.marshall.usc.edu/.../registration-information-interest-lists | ✅ |
| BAEP | Entrepreneurship (Lloyd Greif Center) | students.marshall.usc.edu/.../registration-information-interest-lists | ✅ |
| BUCO (+FBE, DSO, MOR, MKT) | Business Communication | students.marshall.usc.edu/.../registration-information-interest-lists | ✅ |

### Annenberg School for Communication and Journalism

| Dept Code | Name | Source URL | Verified |
|---|---|---|---|
| COMM | Communication | annenberg.usc.edu/current-students/faq/faq-communication | ✅ |
| JOUR (+PREL, ASCJ) | Journalism / Public Relations | annenberg.usc.edu/current-students/faq/faq-journalism | ✅ |

### Dornsife College of Letters, Arts and Sciences — source hub: [dornsife.usc.edu/dash/d-clearance-info/](https://dornsife.usc.edu/dash/d-clearance-info/)

Most Dornsife departments below cite this same central hub as their `source_url`, plus their own department-specific form/contact.

| Dept Code | Name | Source URL | Verified |
|---|---|---|---|
| PSYC | Psychology | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| BISC | Biological Sciences | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| GESM (+FESM) | GE Seminars & GE Departmental Courses | dornsife.usc.edu/ge/registration/ | ✅ |
| AMST | American Studies and Ethnicity | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| ARCG | Archaeology | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| AHIS | Art History | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| CLAS | Classics | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| COLT | Comparative Literature | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| EALC | East Asian Languages and Cultures | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| ENGL | English | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| FREN (+ITAL) | French and Italian | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| SWMS | Gender and Sexuality Studies | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| GERM | German | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| HEBR | Hebrew | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| JS | Jewish Studies | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| LAT | Latin | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| PHIL | Philosophy | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| PORT | Portuguese | dornsife.usc.edu/dash/d-clearance-info/ | ❌ unverified |
| REL | Religion | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| RUSS | Russian | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| SPAN | Spanish | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| WRIT | Writing | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| ANTH | Anthropology | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| ECON | Economics | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| ENST | Environmental Studies | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| HIST | History | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| IR | International Relations | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| LING | Linguistics | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| MDES (+ARAB) | Middle East Studies | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| POSC | Political Science | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| SOCI | Sociology | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| SSCI | Spatial Sciences | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| CGSC | Cognitive Science | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| HBIO | Human Biology | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| NEUR | Neurobiology / Neuroscience | dornsife.usc.edu/usc-neuroscience/neur-490-directed-research/ | ✅ |
| QBIO | Quantitative and Computational Biology | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| CHEM | Chemistry | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| GEOL | Earth Sciences | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| MATH | Mathematics | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| PHYS (+ASTR) | Physics and Astronomy | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |
| MDA (+INDS, FESM) | Media Arts / Interdisciplinary Studies (GE Office) | dornsife.usc.edu/ge/registration/ | ✅ |
| DORN | *(fallback)* Dornsife departments not separately listed | dornsife.usc.edu/dash/d-clearance-info/ | ✅ |

The `DORN` entry is a `type: "school_fallback"` record — it applies when a Dornsife course's prefix isn't one of the explicitly-listed `dept_code`s above. It covers prefixes like `ARCH`, `ARHI`, `EASC`, `GEND`, `INTL`, `JWST`, `LATS`, `POLS`, `RELI` that don't have their own dedicated entry.

### Other schools

| Dept Code | Name / School | Source URL | Verified |
|---|---|---|---|
| PPD | Public Policy & Development (Price) | priceschool.usc.edu/students/registration-d-clearance/undergraduate/ | ✅ |
| CTPR (+CTCS, CTIN, CTAN) | Cinematic Arts (SCA) | cinema.usc.edu/degrees/minor/dclearanceContacts.cfm | ✅ |
| MUSC | Music (Thornton) | music.usc.edu/students/advising-process-majors/ | ✅ |
| ARCH | Architecture | arch.usc.edu/d-clearance | ✅ |
| DANC | Dance (Kaufman) | kaufman.usc.edu/student-affairs/ | ✅ |
| THTR | Dramatic Arts (SDA) | dramaticarts.usc.edu/get-to-know-admissions-and-student-services/ | ✅ |
| ARLT (+RADS, FINE) | Art (Roski) | roski.usc.edu/d-clearance-for-spring-2026-2/ | ✅ |
| SOWK | Social Work | dworakpeck.usc.edu/student-life/enrollment-advisement-services/registration-information | ✅ |
| GERO | Gerontology (Leonard Davis) | gero.usc.edu | ✅ |
| HP (+GHTH, PREV) | Health Promotion and Disease Prevention (Keck) | keck.usc.edu/pphs/education/bachelor-of-science/ | ❌ unverified |
| MEDS | Minor in Health Care Studies (Keck) | keck.usc.edu/medical-education/mhcs-forms/ | ✅ |
| BKPH (+BKN, PT) | Biokinesiology and Physical Therapy (Chan) | chan.usc.edu | ❌ unverified |
| OT (+OCTH) | Occupational Science and Occupational Therapy (Chan) | chan.usc.edu | ❌ unverified |
| IYA | Iovine and Young Academy | iovine-young.usc.edu/learn/undergraduate/academy-non-major-course-offerings | ✅ |

`HP` and `MEDS` are distinct Keck programs, not variants of the same entry: `HP` is the Health Promotion and Disease Prevention Studies major/BS, while `MEDS` is the standalone Minor in Health Care Studies, with its own D-clearance form and process.

## Unverified entries (`verified: false`) — treat with extra caution

4 of 74 entries lack manual confirmation against a live page:

1. **PORT** (Portuguese) — source: dornsife.usc.edu/dash/d-clearance-info/
2. **HP** (Health Promotion, Keck) — source: keck.usc.edu/pphs/education/bachelor-of-science/
3. **BKPH** (Biokinesiology/PT, Chan) — source: chan.usc.edu (no dedicated undergrad D-clearance page)
4. **OT** (Occupational Science/Therapy, Chan) — source: chan.usc.edu (contact changes every term)

`GERO` and `IYA` were confirmed on 2026-08-10 directly against their live department pages (see below) and moved to `verified: true`.

## Cross-cutting notes captured in the data

- **GESM/GE-managed courses** are a special case: a GE office D-clearance *guarantees* a seat, unlike department D-clearances which do not.
- Several departments **share a single Google Form or contact** across course prefixes (e.g. `IR`/`POSC` share the same Directed Research form and contact "Karin Amundsen"; `ARCG`/`REL` share a form link).
- Language departments (FREN, GERM, RUSS, SPAN) uniformly require a **placement exam** before Level 1 D-clearance if the student has prior language experience.
- Viterbi departments distinguish course sections by suffix: **`D`** = D-clearance required, **`R`** = open/registrar enrollment.

## File field reference

Each department entry may include: `dept_code`, `dept_name`, `school`, `also_covers_prefixes`, `priority_note`, `clearance_required_for`, `how_to_get_clearance`, `form_link`, `contact_email`, `contact_office`, `contact_phone`, `typical_turnaround`, `tips`, `source_url`, `verified`. School-fallback entries additionally use `type: "school_fallback"` and `covers_prefixes` instead of `dept_code`-based matching.
