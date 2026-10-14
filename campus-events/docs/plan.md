# Campus Event Management System — Original Plan (Requirements)

This is the requirements and design plan the team wrote **before** building, kept as written (dated 14 Oct 2026).
The section below lists where the final build differs and why; everything after it is the original plan.

## Plan vs. what we built

| Plan said | What we built | Why it changed |
|---|---|---|
| SQLite (`events.db`, `schema.sql`, `BEGIN IMMEDIATE`) | One JSON file (`data/events.json`) with a shared lock and atomic writes | Simpler to set up and to read during the demo; the lock gives the same "check and write together" guarantee within one server |
| Role switcher in the sidebar, no login (A8, AD-6) | Staff login for Admin and Requesters; attendees use the public view with no login | Approve, reject and cancel change what everyone can book, so they must be tied to a real person; attendees keep a friction-free landing page |
| Seed user "Guest (Attendee)" | No attendee accounts | Attendees are anonymous visitors |
| Same-day events only (A9) | Multi-day events allowed | Hackathons often run overnight; the overlap rule already handles multi-day windows, so the restriction added risk and no value |
| Validation on submit (M4) | Live checks as you type (Submit disabled while invalid) **and** a re-check on submit | Conflicts are visible before submission (BC3); the re-check still catches a slot taken in the meantime |
| `rules/` had validation, venues, workflow, models | Added `rules/queries.py` (read-only views and login) and top-level `auth.py` (password hashing) | Needed for login; keeps reads separate from writes |
| `tests/test_rules.py` | Split per the 7-person plan: `test_validation.py`, `test_workflow.py`, `test_venues.py`, `test_flow_e2e.py` (also drives the real UI headlessly) | Matches file ownership; UI flows are tested, not just functions |
| Plain Streamlit look | Team design system applied (`design-system/`, `ui/theme.py`) | Consistent, monochrome UI |
| Open decisions (section 7) | All resolved; see the README "Assumptions" | — |

Not built from the plan: S1 (withdraw pending), S2 (edit venues), S3 (status history), S4 (filters beyond status), and the bonus B1.

---

## 1. Problem statement

The university has no single, trustworthy record of which venue is booked, blocked or free at a given time, so event requests conflict, stall and go unreviewed.

**Context.** The university runs many kinds of campus events: technical workshops, hackathons, placement sessions, club activities, cultural programmes and student competitions. They differ in duration, expected participation, venue requirements and organisational needs. Today they are coordinated through messages, spreadsheets and informal communication.

Problems observed as volume grows:

| # | Symptom | Root cause |
|---|---|---|
| P1 | Conflicting venue requests | No central overlap check |
| P2 | Venues chosen without regard to suitability or capacity | No validation of capacity or venue fit |
| P3 | Limited visibility into request status | No tracked request lifecycle |
| P4 | Delays in reviewing and confirming events | No defined review step or reviewer queue |
| P5 | Venues stay unavailable after cancellations | Venue commitment is not released automatically |
| P6 | Temporary unavailability (maintenance, renovation) | Venue blocks are not recorded |
| P7 | Stakeholders need different information and capabilities | No role-based views or actions |

**Problem to solve (one line).** Build a locally runnable system that lets campus users request a venue for an event, stops invalid or conflicting requests before submission with a clear reason, routes every submitted request through review and approval, shows confirmed events to attendees, and keeps venue availability accurate as requests are approved, rejected or cancelled.

**Goal.** Support a meaningful campus event lifecycle, from an initial request to an appropriate outcome. Multiple approaches are valid; the solution must be internally consistent, usable and explainable by the team.

## 2. Users and stakeholders

Three roles cover every capability the brief names. Review and approval (BC5) are one step, owned by the Admin, who also manages venues.

| Role | Who | Needs | Key actions |
|---|---|---|---|
| Requester | Students, club leads, faculty, placement cell, event organisers | Book a suitable venue; know the status of their requests | Browse venues and availability; submit request; view own request status; cancel own confirmed event (assumption) |
| Admin (Reviewer + Approver) | Venue manager, student affairs or facilities office, authorised faculty | Decide on requests quickly; keep venue data and availability accurate | View Pending queue; approve (event becomes Confirmed) or reject with reason; manage venues (name, type, capacity); block or unblock venues for maintenance or renovation; cancel any confirmed event |
| Attendees / Participants | Students, staff, guests | Know which events are happening, when and where | View confirmed events and venue schedule (read-only) |

**Workflow across roles:** Requester submits (Pending) → Admin approves (Confirmed) or rejects (Rejected) → Requester or Admin may cancel a Confirmed event (Cancelled) → Attendees see Confirmed events. Pending requests hold the venue slot; Rejected and Cancelled release it.

The brief requires that "an appropriate end user" can cancel a confirmed event (BC7); this doc assumes Requester (own events) and Admin (any event), to be confirmed in section 7.

## 3. Functional requirements

Every FR traces to one of the ten business conditions (BC) in the brief or to a deliverable; BC-mapped FRs are mandatory.

**Event request and data**

| ID | Requirement | Source |
|---|---|---|
| FR-01 | An event request records title, event type, organiser/requester, expected attendance, venue, start date-time and end date-time. | BC1 |
| FR-02 | End date-time must be after start date-time; otherwise the request is blocked with a reason. | BC1, BC10 |
| FR-03 | Event types include technical workshop, hackathon, placement session, club activity, cultural programme, student competition (extensible). | Context |

**Validation before submission**

| ID | Requirement | Source |
|---|---|---|
| FR-04 | Block a request whose time overlaps an active (pending) request or confirmed event at the same venue. | BC2, BC3 |
| FR-05 | Overlap rule: new_start < existing_end AND new_end > existing_start. | BC2 |
| FR-06 | Block a request whose time overlaps a venue block (maintenance, renovation, other operational restriction). | BC4 |
| FR-07 | Block a request whose expected attendance exceeds venue capacity. | BC10, P2 |
| FR-08 | Every blocked request shows a clear, specific reason (e.g. which booking or block it clashes with, or the capacity shortfall) and is not saved as submitted. | BC3, BC10 |
| FR-09 | Partial, split bookings and automatic alternative venue suggestions are not provided. | BC9 |

**Review lifecycle**

| ID | Requirement | Source |
|---|---|---|
| FR-10 | A successfully submitted request enters Pending status and holds the venue slot. | BC2, BC5 |
| FR-11 | The Admin can approve a Pending request; it becomes a Confirmed event. | BC5 |
| FR-12 | The Admin can reject a Pending request with a reason; it becomes Rejected and closed. | BC6 |
| FR-13 | Rejection releases the venue slot immediately for other valid requests. | BC6 |
| FR-14 | Rejected requests cannot be edited or reopened; revised details require a new request. | BC6 |
| FR-15 | The Requester (own event) or Admin (any event) can cancel a Confirmed event; it becomes Cancelled. | BC7 |
| FR-16 | Cancellation releases the venue slot immediately. | BC8 |
| FR-17 | Only these transitions are allowed: Pending → Confirmed, Pending → Rejected, Confirmed → Cancelled. Any other transition is refused. | BC5–BC8 |
| FR-18 | Only the Admin can approve or reject; a Requester or Attendee attempting it is refused. | BC5 |

**Venues and visibility**

| ID | Requirement | Source |
|---|---|---|
| FR-19 | Admin maintains venues with name, type and capacity. | Initial data |
| FR-20 | Admin can add a venue block (start, end, reason) and remove it. | BC4 |
| FR-21 | Requesters can see the status of their requests (Pending, Confirmed, Rejected with reason, Cancelled). | P3 |
| FR-22 | The Admin sees a queue of Pending requests to approve or reject. | P4 |
| FR-23 | Attendees / Participants can view confirmed events and each venue's schedule (read-only). | P7 |
| FR-24 | Requester and Admin can view a venue's full schedule: confirmed events, held slots and blocks. | P1, P7 |
| FR-25 | Each role sees only its own screens and actions (simple role selection or login). | P7 |
| FR-26 | The system loads the initial campus data (section 6) on first run. | Initial data |

**Bonus (only if core works)**

| ID | Requirement | Source |
|---|---|---|
| FR-B1 | One extra capability that makes the tool more useful, e.g. notifications, analytics, calendar export, smart suggestions. To be chosen by the team. | Bonus |

## 4. Non-functional requirements

The brief values reliability and explainability over size, so NFRs focus on consistency, clarity and local operation.

| ID | Category | Requirement | Source |
|---|---|---|---|
| NFR-01 | Data consistency | A venue is never committed twice for overlapping time; state and availability always agree. | BC2 |
| NFR-02 | Reliability | Validation runs at the point of submission against current saved data, not stale UI data. | BC3 |
| NFR-03 | Persistence | Data survives app restart using a lightweight local store (SQLite, JSON or CSV). | Brief |
| NFR-04 | Usability | Every error states what failed and why in plain language. | BC10 |
| NFR-05 | Usability | Each of the three roles (Requester, Admin, Attendee) sees only the information and actions relevant to it. | P7 |
| NFR-06 | Maintainability | Business rules live in one module, separate from the UI, so they can be tested and explained. | Deliverable 1 |
| NFR-07 | Testability | Core rules (overlap, capacity, blocks, transitions) are covered by automated tests. | Demo: testing performed |
| NFR-08 | Explainability | Every team member can explain the code, one business rule, one assumption and how it was validated. | Demo |
| NFR-09 | Portability | Runs locally with documented prerequisites and a single startup command. | Deliverable 2 |
| NFR-10 | Performance | Responses feel instant for campus-scale data (tens of venues, hundreds of events). | Assumption |
| NFR-11 | Traceability | Repository history shows incremental, shared collaboration. | Constraints |

## 5. Constraints

All constraints below are stated in the brief and are fixed.

| # | Constraint |
|---|---|
| C1 | 90 minutes to complete. |
| C2 | Locally runnable prototype with a UI (Streamlit, web-based or any framework). |
| C3 | Python preferred; C++ or Java acceptable. |
| C4 | No cloud deployment, external APIs, paid services, complex infrastructure, or access to university production systems. |
| C5 | Persistence: in-memory, local files, JSON, CSV, SQLite or another lightweight local approach. |
| C6 | Authentication optional; if implemented, explain why it was prioritised. |
| C7 | Shared GitHub repository with meaningful, incremental collaboration. Commit count alone does not measure contribution; history may be used as evidence of how work was divided, integrated and validated. |
| C8 | Tools: VS Code + GitHub Copilot. AI tools are allowed, but the team must understand, review, run, validate and explain every artefact. |
| C9 | Team size as announced. |
| C10 | Bonus feature counts only if core functionality is demonstrably working. |

Evaluation weights: Problem Understanding 20%, Implementation & Completeness 20%, AI Usage 20%, Collaboration & Communication 20%, Quiz 20% (conducted earlier). A smaller, reliable, well-explained solution may score higher than a larger one with code the team cannot explain.

## 6. Initial campus data

The system must start with these five venues; teams may add reasonable details or extra sample records for testing and demonstration.

| Venue | Type | Capacity | Current information |
|---|---|---|---|
| Seminar Hall A | Seminar Hall | 120 | Confirmed event on 4 Aug 2026, 10:00–12:00 |
| Main Auditorium | Auditorium | 500 | Available |
| Conference Room C | Conference Room | 40 | Blocked for renovation on 4 Aug 2026, 09:00–18:00 |
| Central Amphitheatre | Open Venue | 300 | Available |
| Innovation Lab | Computer Lab | 60 | Confirmed event on 6 Aug 2026, 14:00–17:00 |

These records give ready-made demo cases: a request at Seminar Hall A on 4 Aug 11:00–13:00 must fail (overlap); any request at Conference Room C on 4 Aug 09:00–18:00 must fail (renovation); 200 attendees at Innovation Lab must fail (capacity).

## 7. Scope, deliverables and open decisions

Explicitly out of scope (BC9): partial bookings, split bookings, automatic alternative venue suggestions.

**Deliverables**

1. **Working prototype:** locally runnable, connected workflows, consistent event and venue states, business validations, conflict/failure handling; at least one end-to-end flow demonstrated.
2. **GitHub repository:** source code, run instructions (prerequisites, setup, startup), documented assumptions, scope prioritised, features excluded, trade-offs, known limitations, consulting pitch.
3. **Two-slide consulting pitch:**
   1. Slide 1, Problem understanding: problem, stakeholders/personas, workflows prioritised, business rules discovered, key assumptions, scope for 90 minutes.
   2. Slide 2, Solution and engineering decisions: approach, design decisions, trade-offs, testing/validation, known limitations, next improvements.
4. **Final demonstration:** problem understanding, stakeholders and workflows, working app, one successful end-to-end scenario, one conflict/invalid/failure scenario, design decisions, testing, assumptions and trade-offs, limitations, next steps. Evaluators may add a scenario and question any member on their contribution, one business rule, one part of the solution, one assumption or trade-off, and how their work was validated.

**Open decisions for the team (document whichever is chosen)**

- [ ] Are back-to-back bookings (10:00–12:00 then 12:00–14:00) allowed? Suggested: yes, using strict overlap.
- [ ] Confirm cancel rights: Requester (own events) and Admin (any event)?
- [ ] Can a requester withdraw their own Pending request?
- [ ] Decided: Reviewer, Approver and Admin are one role (Admin).
- [ ] Do Attendees only view events, or also register / RSVP (bonus candidate)?
- [ ] Are requests for past date-times blocked?
- [ ] Is a rejection reason mandatory?
- [ ] Authentication or a simple role switcher across the three roles? Brief says optional; a role switcher is faster.
- [ ] What happens to existing Pending/Confirmed bookings when a new venue block overlaps them?
- [ ] Which bonus feature, if time allows?

## 8. MVP definition

The MVP is a single-user, locally run Streamlit app on SQLite. It delivers the full request lifecycle (submit, validate, approve or reject, cancel) for three roles, with every business condition enforced in one tested rules module.

**MVP goal.** Demonstrate one reliable end-to-end flow (request → approve → confirmed → cancel → slot released) and every failure case (overlap, renovation block, capacity, bad times, invalid transition) with a clear reason on screen.

**Tech stack**

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Preferred by brief (C3) |
| UI | Streamlit | Fastest local UI in Python; no frontend build (C1, C2) |
| Storage | SQLite via sqlite3 (standard library) | Survives restart, no install, no server (C4, C5, NFR-03) |
| Tests | pytest | Quick rule tests to show in the demo (NFR-07) |
| Access | Role switcher in sidebar, no login | Auth is optional (C6); three roles demo faster without passwords |

**Decisions the MVP locks in (documented as assumptions in the README)**

| # | Decision |
|---|---|
| A1 | Back-to-back bookings are allowed: overlap is strict, new_start < existing_end AND new_end > existing_start. |
| A2 | Past start times are not blocked in the MVP: the brief's seed data (Aug 2026) is already in the past, so the rule would break every demo case. Listed as a known limitation. |
| A3 | Only Pending and Confirmed bookings, plus venue blocks, hold a slot. |
| A4 | A rejection reason is mandatory. |
| A5 | Requester can cancel only their own Confirmed events; Admin can cancel any. |
| A6 | A Requester cannot withdraw a Pending request in the MVP (Should-have if time allows). |
| A7 | Admin cannot add a venue block that overlaps a Pending or Confirmed booking; the conflicting bookings are listed and must be resolved first. |
| A8 | Users are picked from a small seeded list (e.g. 2 requesters, 1 admin); identity is the selected name, not a login. |
| A9 | Event start and end fall on the same day (no multi-day events). |
| A10 | Expected attendance must be a whole number of at least 1. |

## 9. MVP features

Ten Must-have features carry every mandatory FR; Should-haves are built only after all Must-haves pass their demo scenario.

| ID | Feature | Role | Priority |
|---|---|---|---|
| M1 | Seed data loader: 5 venues, 1 renovation block, 2 confirmed events, sample users | System | Must |
| M2 | Role and user switcher in sidebar | All | Must |
| M3 | New request form: title, event type, attendance, venue, date, start, end | Requester | Must |
| M4 | Validation on submit: time order, same day, attendance ≥ 1, capacity, venue block, overlap; clear reason on failure | Requester | Must |
| M5 | My requests: list with status and rejection reason | Requester | Must |
| M6 | Cancel own Confirmed event | Requester | Must |
| M7 | Pending queue: approve, or reject with mandatory reason | Admin | Must |
| M8 | Venue blocks: add and remove maintenance or renovation blocks | Admin | Must |
| M9 | All events: list and cancel any Confirmed event | Admin | Must |
| M10 | Confirmed events list and per-venue schedule (events, holds, blocks) | Attendee (read-only), all roles | Must |
| S1 | Requester withdraws own Pending request | Requester | Should |
| S2 | Admin adds or edits venues | Admin | Should |
| S3 | Status history: who changed what, when | Admin | Should |
| S4 | Filters on lists (by venue, date, status) | All | Should |
| B1 | Bonus: venue availability finder or utilisation analytics (team to pick one) | All | Bonus |

## 10. FR traceability

All 26 core FRs are covered by the MVP; only FR-19 (venue editing) is partly deferred, since the seeded venues meet the brief.

| FR | Short name | MVP feature | Module | Coverage |
|---|---|---|---|---|
| FR-01 | Request fields | M3 | app.py, db.py | Full |
| FR-02 | End after start | M4 | rules.py | Full |
| FR-03 | Event types | M3 (dropdown) | app.py | Full |
| FR-04 | Block overlap with Pending/Confirmed | M4 | rules.py | Full |
| FR-05 | Overlap formula | M4 | rules.py | Full |
| FR-06 | Block overlap with venue block | M4 | rules.py | Full |
| FR-07 | Capacity check | M4 | rules.py | Full |
| FR-08 | Clear failure reason, nothing saved | M4 | rules.py, app.py | Full |
| FR-09 | No split/partial/alternatives | Not built, by design | — | Full (exclusion) |
| FR-10 | Pending holds slot | M3, M4 | rules.py | Full |
| FR-11 | Admin approves → Confirmed | M7 | rules.py, app.py | Full |
| FR-12 | Admin rejects with reason | M7 | rules.py, app.py | Full |
| FR-13 | Rejection releases slot | M7 (status excluded from overlap) | rules.py | Full |
| FR-14 | Rejected is closed | No edit or reopen action exists | rules.py | Full |
| FR-15 | Cancel Confirmed (Requester own / Admin any) | M6, M9 | rules.py, app.py | Full |
| FR-16 | Cancellation releases slot | M6, M9 | rules.py | Full |
| FR-17 | Allowed transitions only | All status changes go through one function | rules.py | Full |
| FR-18 | Only Admin approves/rejects | M2, M7 | rules.py | Full |
| FR-19 | Admin maintains venues | M1 (seeded), S2 (edit) | db.py | Partial: edit is Should |
| FR-20 | Venue blocks add/remove | M8 | rules.py, app.py | Full |
| FR-21 | Requester sees status | M5 | app.py | Full |
| FR-22 | Admin Pending queue | M7 | app.py | Full |
| FR-23 | Attendee read-only view | M10 | app.py | Full |
| FR-24 | Full venue schedule | M10 | app.py | Full |
| FR-25 | Role-specific screens | M2 | app.py | Full |
| FR-26 | Seed initial data | M1 | db.py | Full |
| FR-B1 | Bonus feature | B1 | — | After core |

## 11. NFR and constraint traceability

Every NFR and constraint has a concrete mechanism in the MVP; none relies on goodwill.

**NFRs**

| NFR | How the MVP meets it | Verified by |
|---|---|---|
| NFR-01 Data consistency | All writes go through rules.py; approve, submit and block re-check overlap inside one SQLite transaction | Test: two overlapping submits, second fails |
| NFR-02 Validation on current data | Checks query the database at submit time, never cached UI state | Test + demo |
| NFR-03 Persistence | SQLite file events.db; seeded only if empty | Restart app, data still there |
| NFR-04 Clear errors | rules.py returns (ok, reason); UI shows reason via st.error | Demo failure scenarios |
| NFR-05 Role-specific views | Sidebar role picks which pages and buttons render; rules.py also checks role | Test: requester approve is refused |
| NFR-06 Rules separate from UI | rules.py has no Streamlit imports | Code review |
| NFR-07 Automated tests | pytest suite on rules.py with a temporary DB | pytest passes |
| NFR-08 Explainability | ~3 small files; each member owns one and its tests | Demo Q&A |
| NFR-09 Portability | requirements.txt + streamlit run app.py | Fresh-clone run |
| NFR-10 Performance | Indexed queries on venue and time; campus-scale data | Manual check |
| NFR-11 Traceability | Feature branches or small commits per member | Git history |

**Constraints**

| Constraint | How the MVP complies |
|---|---|
| C1 90 minutes | Ten Must features only; Should/Bonus only after Must passes |
| C2 Local UI | Streamlit on localhost |
| C3 Python | Python only |
| C4 No cloud/APIs/paid services | Standard library + Streamlit + pytest; no network calls |
| C5 Lightweight storage | Single SQLite file |
| C6 Auth optional | Role switcher; reason documented (speed, demo clarity) |
| C7 Shared GitHub repo | One repo, one module per member, incremental commits |
| C8 AI use with ownership | AI drafts code; team reviews, runs tests, documents AI usage in README |
| C9 Team size | Plan in section 13 scales by merging owners |
| C10 Bonus after core | B1 gated on all Must scenarios passing |

## 12. Code structure and demo scenarios

Three source files and one test file keep the MVP small enough for every member to explain. For the seven-person team these become small packages; see section 22.

| File | Responsibility |
|---|---|
| db.py | SQLite schema (venues, venue_blocks, users, requests), connection, seed data on first run |
| rules.py | All validation, overlap check and status transitions; returns (ok, reason); no UI code |
| app.py | Streamlit UI: role switcher and the pages for each role; calls rules.py only |
| tests/test_rules.py | pytest cases for every rule below |
| README.md | Run steps, assumptions A1–A10, scope, exclusions, trade-offs, limitations, AI usage, pitch |

Request statuses: PENDING, CONFIRMED, REJECTED, CANCELLED.

**Demo and test scenarios (all on seed data)**

| # | Scenario | Expected result | Rule |
|---|---|---|---|
| T1 | Request Main Auditorium, 5 Aug 2026 10:00–13:00, 300 people; Admin approves; Requester cancels | Pending → Confirmed → Cancelled; slot free again | BC5, BC7, BC8 |
| T2 | Seminar Hall A, 4 Aug 2026 11:00–13:00 | Blocked: overlaps confirmed event 10:00–12:00 | BC2, BC3 |
| T3 | Seminar Hall A, 4 Aug 2026 12:00–14:00 | Allowed: back-to-back (A1) | A1 |
| T4 | Conference Room C, 4 Aug 2026 14:00–15:00 | Blocked: renovation 09:00–18:00 | BC4 |
| T5 | Innovation Lab, 200 people | Blocked: capacity 60 | BC10 |
| T6 | End time before start time | Blocked: invalid time range | BC1 |
| T7 | Two requests for the same free slot | First Pending; second blocked by the Pending hold | BC2 |
| T8 | Admin rejects the Pending one from T7; new request for same slot | Rejected; new request now allowed | BC6 |
| T9 | Requester tries to approve, or cancel a Rejected request | Refused: wrong role / invalid transition | FR-17, FR-18 |
| T10 | Admin adds a block over an existing Confirmed event | Refused, conflicting event listed | A7 |

## 13. 90-minute build plan and team split

Core must be demo-ready by minute 60; the last 30 minutes are for testing, Should/Bonus, README and slides. The member split below is superseded by the seven-person split in section 22; the milestones still apply.

| Member | Owns | Files |
|---|---|---|
| Member 1 | Data model, seed data, persistence | db.py |
| Member 2 | Business rules and transitions | rules.py |
| Member 3 | UI for Requester and Attendee | app.py (requester, attendee pages) |
| Member 4 | UI for Admin; tests; README and pitch | app.py (admin pages), tests/, README.md |

| Time (min) | Milestone | Done when |
|---|---|---|
| 0–10 | Repo, skeleton files, agree on schema and rules.py function signatures | All members can run an empty Streamlit app |
| 10–35 | db.py with seed; rules.py with all checks; UI pages stubbed | T2–T6 pass in pytest |
| 35–60 | Wire UI to rules: submit, queue, approve/reject, cancel, blocks, schedule | T1 runs end to end in the UI |
| 60–70 | Run T1–T10 in UI and pytest; fix bugs | All ten scenarios pass |
| 70–80 | Should-haves, then Bonus if time | Core still passes |
| 80–90 | README (assumptions, trade-offs, limitations, AI usage), two slides, demo rehearsal | Each member can explain one rule and how it was tested |

Known limitations of the MVP: no login (role switcher only); past dates not blocked; single-day events only; no notifications; venue editing deferred; single-user local app, not concurrent multi-user.

## 14. Solution architecture overview

The MVP is a layered monolith: one Python process on the user's machine, a Streamlit UI on top, a pure-Python rules layer in the middle, and a single SQLite file underneath.

**Architecture principles**

- **Rules in one place.** Every business condition (BC1–BC10) is enforced in rules.py; the UI never decides.
- **Check and write together.** Validation and the write happen in the same database transaction, so availability can't change in between.
- **Fail loudly and specifically.** Every refusal carries a human-readable reason.
- **Local and dependency-light.** Python standard library + Streamlit + pytest; no network, cloud or paid services.
- **Replaceable layers.** The UI or the database can be swapped later without touching the rules.

Requests flow strictly downward: the UI calls rules.py, which alone talks to db.py; tests exercise rules.py directly against a throwaway database.

## 15. Component design

Each module has one job and depends only on the layer below it: app.py → rules.py → db.py → SQLite.

| Component | Layer | Responsibility | Must not |
|---|---|---|---|
| app.py | Presentation | Role/user switcher, forms, lists, buttons; shows Result.reason; calls st.rerun() after writes | Contain business rules or SQL |
| rules.py | Domain / service | Validation, overlap detection, role checks, status transitions; opens a transaction per write | Import Streamlit |
| db.py | Data access | Connection, schema, seed, plain read/write queries | Make business decisions |
| SQLite events.db | Storage | Durable data; CHECK and FK constraints as last line of defence | — |
| tests/test_rules.py | Verification | pytest suite against a temporary database | Touch events.db |

**rules.py public functions** (every write returns `Result(ok: bool, reason: str, id: int | None)`)

| Function | Who may call | What it does |
|---|---|---|
| validate_request(conn, venue_id, start, end, attendance) | Any | Returns all reasons a request would fail; used for live feedback and by submit |
| find_conflicts(conn, venue_id, start, end, exclude_id=None) | Internal | Pending/Confirmed requests and blocks overlapping the window |
| submit_request(conn, user, data) | Requester | Validates, then inserts as PENDING, in one transaction |
| approve(conn, user, request_id) | Admin | PENDING → CONFIRMED; re-checks conflicts excluding itself |
| reject(conn, user, request_id, reason) | Admin | PENDING → REJECTED; reason required |
| cancel(conn, user, request_id) | Requester (own) / Admin | CONFIRMED → CANCELLED |
| add_block(conn, user, venue_id, start, end, reason) | Admin | Inserts a venue block; refused if it overlaps Pending/Confirmed requests (A7) |
| remove_block(conn, user, block_id) | Admin | Deletes a venue block |

All status changes go through one private `_transition(conn, user, request_id, to_status, reason=None)`, which holds the allowed-transition table and the role table. This is the single place FR-17 and FR-18 are enforced.

db.py functions: get_connection(path), init_schema(conn), seed_if_empty(conn), list_users, list_venues, get_venue, list_requests(**filters), get_request, insert_request, update_request_status, list_blocks(venue_id=None), insert_block, delete_block.

## 16. Data model

Four tables. A confirmed "event" is the same row as its request with status CONFIRMED, so a booking's whole history lives in one place.

| Table | Column | Type / constraint |
|---|---|---|
| users | id | INTEGER PK |
| | name | TEXT NOT NULL |
| | role | TEXT CHECK IN ('REQUESTER','ADMIN','ATTENDEE') |
| venues | id | INTEGER PK |
| | name | TEXT NOT NULL UNIQUE |
| | type | TEXT NOT NULL |
| | capacity | INTEGER CHECK > 0 |
| venue_blocks | id | INTEGER PK |
| | venue_id | FK → venues.id |
| | start_dt, end_dt | TEXT 'YYYY-MM-DD HH:MM'; CHECK end_dt > start_dt |
| | reason | TEXT NOT NULL (maintenance, renovation, other) |
| | created_by | FK → users.id |
| event_requests | id | INTEGER PK |
| | title, event_type | TEXT NOT NULL |
| | requester_id | FK → users.id |
| | venue_id | FK → venues.id |
| | attendance | INTEGER CHECK >= 1 |
| | start_dt, end_dt | TEXT 'YYYY-MM-DD HH:MM'; CHECK end_dt > start_dt |
| | status | TEXT CHECK IN ('PENDING','CONFIRMED','REJECTED','CANCELLED') |
| | decision_reason | TEXT NULL (required when REJECTED) |
| | decided_by | FK → users.id NULL |
| | created_at, updated_at | TEXT timestamps |

Indexes: event_requests(venue_id, status, start_dt) and venue_blocks(venue_id, start_dt), the two lookups behind every overlap check.

Overlap query (used by find_conflicts):

```sql
SELECT id FROM event_requests
WHERE venue_id = ? AND status IN ('PENDING','CONFIRMED')
  AND start_dt < :new_end AND end_dt > :new_start
  AND id != :exclude_id;
```

The same predicate runs against venue_blocks. Fixed-width ISO text compares correctly as strings.

Seed: 5 venues from section 6; users Admin, Asha (Requester), Ravi (Requester), Guest (Attendee); 2 CONFIRMED requests (Seminar Hall A 4 Aug 10:00–12:00, Innovation Lab 6 Aug 14:00–17:00); 1 block (Conference Room C 4 Aug 09:00–18:00, renovation).

## 17. Request lifecycle

Four statuses and three transitions, all enforced by _transition in rules.py; any other move is refused.

```
PENDING ──approve──► CONFIRMED ──cancel──► CANCELLED
   └──reject──► REJECTED
```

A failed check never creates a row, so there is no "draft" or "invalid" status to clean up.

## 18. Key flows

Every write follows the same pattern: UI collects input → rules.py opens a transaction → checks role and rules → writes or refuses → UI shows Result and reruns.

**Submit request (Requester)**

1. Requester fills the form; app.py builds start_dt/end_dt from date + times.
2. submit_request starts BEGIN IMMEDIATE (takes the write lock before reading).
3. Checks, all reasons collected: required fields → end after start, same day → attendance ≥ 1 → attendance ≤ venue capacity → no overlapping venue block → no overlapping PENDING/CONFIRMED request.
4. Any failure → ROLLBACK; return Result(False, "Seminar Hall A is booked 10:00–12:00 on 4 Aug (Event: …)"). Nothing is saved.
5. All pass → insert as PENDING, COMMIT; UI shows success and the request appears in My requests and the Admin queue.

**Approve or reject (Admin)**

1. Admin opens the Pending queue (oldest first) and picks a request.
2. Approve → _transition(PENDING → CONFIRMED) inside a transaction; re-runs find_conflicts excluding itself as a safety net.
3. Reject → reason is required; _transition(PENDING → REJECTED); the slot is free because overlap checks ignore REJECTED.

**Cancel (Requester own / Admin any)**

1. User clicks Cancel on a CONFIRMED event.
2. _transition(CONFIRMED → CANCELLED) checks ownership for Requesters.
3. The slot is free immediately, because overlap checks ignore CANCELLED.

**Add venue block (Admin)**

1. Admin enters venue, start, end, reason.
2. add_block runs find_conflicts for PENDING/CONFIRMED requests in that window.
3. Conflicts → refused, listing each one so the Admin can reject or cancel them first (A7). No conflicts → block inserted, and new requests in that window are refused with the block's reason.

## 19. Cross-cutting concerns

The two concerns that decide whether the system is trustworthy are consistency (no double booking) and authorisation (only the right role changes state); both live in rules.py, not the UI.

| Concern | Approach |
|---|---|
| Consistency | Check-then-write inside one BEGIN IMMEDIATE transaction, so two browser tabs submitting the same slot cannot both succeed. PRAGMA foreign_keys = ON; CHECK constraints catch bad rows even if code is wrong. |
| Authorisation | UI hides buttons per role, and rules.py re-checks role and ownership on every write. Hiding alone is not trusted. |
| Error handling | Business failures return Result(ok=False, reason) shown with st.error. Unexpected exceptions are caught in app.py, logged, and shown as a generic message; the transaction rolls back. |
| Validation feedback | All failing reasons are returned together, so the user fixes everything in one go. |
| Time handling | Campus local time (IST), naive, minute precision, stored as 'YYYY-MM-DD HH:MM'. Same-day events only (A9). |
| Double-click / rerun | Submit button inside st.form; success clears the form; the DB check refuses a duplicate overlapping request anyway. |
| Configuration | DB path from env var EVENTS_DB, default events.db; python db.py --reset rebuilds and re-seeds for a clean demo. |
| Logging | Python logging to console: every transition with user, request id, from → to. |
| Testing | pytest fixture creates a fresh DB in tmp_path and seeds it; unit tests for each rule (T2–T10); one flow test for T1; manual UI run of T1–T10 before the demo. |
| AI-assisted code | AI drafts per file; the owner reviews, runs the tests, and notes changes in the README AI-usage section. |

## 20. Architecture decisions

Every decision trades breadth for something the team can build, test and explain in 90 minutes.

| # | Decision | Alternatives rejected | Trade-off accepted |
|---|---|---|---|
| AD-1 | Layered monolith, one process | FastAPI backend + React frontend | No separate API; but rules.py can be wrapped by an API later unchanged |
| AD-2 | Streamlit for UI | Flask + templates; Tkinter | Less layout control and full-page reruns; in exchange, no HTML/JS work |
| AD-3 | SQLite | JSON or CSV files; in-memory | Slightly more setup; in exchange, transactions, constraints and SQL queries for overlaps |
| AD-4 | One event_requests table with a status column | Separate requests and events tables | Request and event share fields; a status filter replaces a join and keeps history in one row |
| AD-5 | Overlap enforced in code within a transaction | DB-level exclusion constraint | SQLite lacks range constraints; the transaction plus tests cover it |
| AD-6 | Role switcher, no login | Username/password auth | No real security; acceptable for a local prototype (C6) and makes the demo faster |
| AD-7 | Return all validation reasons at once | Stop at first failure | Slightly more code; much clearer UX (BC10) |
| AD-8 | Naive local time as ISO text | Timezone-aware UTC storage | Single campus, single timezone; simple string comparison |
| AD-9 | Block cannot overlap active bookings (A7) | Auto-cancel conflicting bookings | Admin does one extra step; no event is cancelled silently |

## 21. Risks and evolution path

The biggest MVP risk is time, not technology; the layering is chosen so each later step replaces one layer without rewriting the rules.

| Risk | Impact | Mitigation |
|---|---|---|
| Core not finished by minute 60 | No working demo | Must-only scope; rules.py and tests first; UI wiring second |
| AI-generated code nobody understands | Lost marks in Q&A | One owner per file; owner runs and explains the tests |
| Streamlit rerun quirks (state lost, double submit) | Confusing demo | st.form, st.session_state for role, DB-level duplicate check |
| Seed dates are in the past | Past-date rule would break demos | Rule dropped for MVP (A2) |
| Merge conflicts in app.py | Lost time | Split admin and requester pages into separate functions; agree signatures at minute 0 |

**Evolution path after the MVP**

1. Real authentication (campus SSO) replacing the role switcher; roles from a directory.
2. Wrap rules.py in a FastAPI service; any web or mobile frontend calls it.
3. Move to PostgreSQL and enforce overlap in the database with an exclusion constraint on a time range.
4. Notifications (email or in-app) on submit, approve, reject, cancel.
5. Calendar export (.ics) and a calendar-grid view per venue.
6. Audit trail table and utilisation analytics.
7. Richer matching: venue equipment and features, multi-day and recurring events, a separate Reviewer role if the university needs two-step approval.

## 22. Seven-person team split and file structure

With seven people, rules.py and db.py become small packages and the UI splits by role, so every member owns separate files and nobody waits on anyone after minute 10. The layers in section 14 are unchanged.

**File structure**

```
campus-events/
├── app.py                  # P1  entrypoint: page config, role/user switcher, routing to ui/
├── rules/                  # domain layer (was rules.py)
│   ├── __init__.py         # P1  re-exports the public functions
│   ├── models.py           # P1  Result, Status, Role, TRANSITIONS, ROLE_PERMISSIONS (the contract)
│   ├── validation.py       # P3  validate_request, find_conflicts
│   ├── venues.py           # P3  add_block, remove_block (A7)
│   └── workflow.py         # P4  submit_request, approve, reject, cancel, _transition
├── db/                     # data access layer (was db.py)
│   ├── __init__.py
│   ├── connection.py       # P2  get_connection, init_schema, transaction() helper
│   ├── schema.sql          # P2  4 tables, CHECK + FK, indexes
│   ├── repository.py       # P2  all read/write queries
│   └── seed.py             # P2  initial campus data; python -m db.seed --reset
├── ui/                     # presentation layer
│   ├── __init__.py
│   ├── components.py       # P6  show_result, status_badge, events_table, datetime_inputs
│   ├── requester.py        # P5  new request form, my requests, cancel own
│   ├── attendee.py         # P5  confirmed events, venue schedule
│   └── admin.py            # P6  pending queue, all events, venue blocks
├── tests/
│   ├── conftest.py         # P7  temp-DB fixture with seed data
│   ├── test_validation.py  # P3  T2–T6
│   ├── test_venues.py      # P3  T10
│   ├── test_workflow.py    # P4  T7–T9
│   └── test_flow_e2e.py    # P7  T1 end to end
├── docs/
│   ├── test_runsheet.md    # P7  manual UI run of T1–T10
│   └── pitch/              # P7  two-slide consulting pitch
├── requirements.txt        # P1  streamlit, pytest
├── .gitignore              # P1  events.db, __pycache__, .venv
└── README.md               # P7  run steps, assumptions, scope, trade-offs, limitations, AI usage
```

**Who owns what**

| Member | Role | Owns | Delivers | Depends on (via contract only) |
|---|---|---|---|---|
| P1 | Tech lead and integrator | app.py, rules/models.py, rules/__init__.py, repo setup | Skeleton with every public signature stubbed by minute 10; role switcher and routing; merges PRs | — |
| P2 | Data engineer | db/ | Schema, transaction helper, repository queries, seed (M1) | models.py |
| P3 | Rules: validation and blocks | rules/validation.py, rules/venues.py, their tests | M4 checks, overlap query use, A7 block rule | Repository signatures |
| P4 | Rules: workflow | rules/workflow.py, its tests | Submit, approve, reject, cancel, transition and role tables (FR-10–FR-18) | validation.py signatures |
| P5 | UI: Requester and Attendee | ui/requester.py, ui/attendee.py | M3, M5, M6, M10 | rules/__init__ signatures, components.py names |
| P6 | UI: Admin and shared components | ui/admin.py, ui/components.py | M7, M8, M9 and shared widgets | rules/__init__ signatures |
| P7 | QA, docs and pitch | tests/conftest.py, tests/test_flow_e2e.py, docs/, README.md | Test fixture, T1 flow test, run sheet, README, slides; Bonus B1 if time | Seed data shape |

**How the work stays concurrent**

1. **Contract first (0–10 min).** P1 pushes the skeleton: every file above exists, every public function has its final signature, a docstring and `raise NotImplementedError`. models.py holds the status, role and transition tables. P2 pushes schema.sql in the same window.
2. **Build against stubs (10–45 min).** Each member works only in their own files on a branch feat/<area>. UI members call the stubbed functions and render placeholder data until the real ones land; rules members write tests first against the fixture.
3. **Small, frequent merges.** Each member opens a PR as soon as one function works; P1 merges to main at least every 15 minutes. Nobody edits another member's file; a needed change is a message to its owner.
4. **Integrate (45–60 min).** Stubs are all replaced; P1 runs T1 end to end in the UI.
5. **Validate (60–75 min).** P7 runs the run sheet T1–T10; each owner fixes failures in their own files.
6. **Finish (75–90 min).** README and slides final (P7 with input from all); every member rehearses explaining their file, one rule and its test.
