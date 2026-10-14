# Campus Event Management System

A locally runnable web app where campus staff request a venue for an event, an Admin reviews the request, and everyone can see which events are confirmed. It stops double bookings, oversized events and bookings in blocked venues **before** a request is submitted, and always says why.

Built for the IIIT Hackathon Challenge (90 minutes, Python, local only).

Our original requirements and design plan, and how the build differs from it: **[docs/plan.md](docs/plan.md)**.

---

## Contents

1. [Quick start](#1-quick-start)
2. [Demo accounts](#2-demo-accounts)
3. [Demo walkthrough](#3-demo-walkthrough)
4. [The problem we solved](#4-the-problem-we-solved)
5. [Stakeholders and what each can do](#5-stakeholders-and-what-each-can-do)
6. [Request lifecycle](#6-request-lifecycle)
7. [Business rules and where they live](#7-business-rules-and-where-they-live)
8. [Architecture](#8-architecture)
9. [Project structure](#9-project-structure)
10. [Data model](#10-data-model)
11. [Rules API (for developers)](#11-rules-api-for-developers)
12. [Authentication](#12-authentication)
13. [Design system](#13-design-system)
14. [Testing](#14-testing)
15. [Assumptions](#15-assumptions)
16. [Scope: built and excluded](#16-scope-built-and-excluded)
17. [Trade-offs](#17-trade-offs)
18. [Known limitations](#18-known-limitations)
19. [Next steps](#19-next-steps)
20. [How AI was used](#20-how-ai-was-used)
21. [Consulting pitch](#21-consulting-pitch)
22. [Contributing](#22-contributing)
23. [Troubleshooting](#23-troubleshooting)

---

## 1. Quick start

**Prerequisite:** Python 3.10 or newer.

```bash
git clone https://github.com/keshavdubeyy/microsoft-hackathon-group5.git
cd microsoft-hackathon-group5/campus-events

python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
streamlit run app.py              # opens http://localhost:8501
```

| Task | Command |
|---|---|
| Run the app | `streamlit run app.py` |
| Run all tests | `python -m pytest -q` |
| Reset data to the initial campus data | `python -m db.seed --reset` (or **Reset demo data** in the sidebar as Admin) |
| Reset and add extra pending, rejected and cancelled requests to review | `python -m db.seed --reset --demo` |
| Use a different data file | set `EVENTS_DB=path/to/file.json` before starting |

On first run the app creates `data/events.json` and fills it with the brief's campus data. The `data/` folder is git-ignored.

---

## 2. Demo accounts

Anyone who opens the portal sees the public **attendee view** without logging in. Staff log in from **Staff login** in the sidebar.

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `asha` | `asha123` | Requester (owns the seeded "AI Workshop") |
| `ravi` | `ravi123` | Requester (owns the seeded "Python Coding Bootcamp") |

### Initial campus data

| Venue | Type | Capacity | Starting state |
|---|---|---|---|
| Seminar Hall A | Seminar Hall | 120 | Confirmed "AI Workshop", 4 Aug 2026, 10:00–12:00 (Asha) |
| Main Auditorium | Auditorium | 500 | Available |
| Conference Room C | Conference Room | 40 | Blocked for renovation, 4 Aug 2026, 09:00–18:00 |
| Central Amphitheatre | Open Venue | 300 | Available |
| Innovation Lab | Computer Lab | 60 | Confirmed "Python Coding Bootcamp", 6 Aug 2026, 14:00–17:00 (Ravi) |

---

## 3. Demo walkthrough

Start from fresh data: `python -m db.seed --reset`.

**Successful end-to-end flow**

1. Open the app: the public **Confirmed events** list shows the two seeded events.
2. Log in as `asha`. Go to **New request**: "Freshers Hackathon", Hackathon, Main Auditorium, 5 Aug 2026 10:00–13:00, 300 people. The form says the venue is available. Click **Submit request**: it is now *Pending*.
3. Log out, log in as `admin`. **Review queue** shows the request. Click **Approve**: it is now *Confirmed*.
4. Log out. The public view now lists "Freshers Hackathon".
5. Log in as `asha`, **My requests**, **Cancel event**: it is *Cancelled* and the slot is free again.

**Failure scenarios (all caught before submission, with the reason shown)**

| Try this as `ravi` | What you see |
|---|---|
| Seminar Hall A, 4 Aug 11:00–13:00 | Clashes with confirmed event "AI Workshop" 10:00–12:00. Submit disabled. |
| Conference Room C, 4 Aug 14:00–15:00 | Venue unavailable (Renovation). |
| Innovation Lab, 200 people | Exceeds capacity of 60. |
| End time before start time | End must be after start. |
| Seminar Hall A, 4 Aug 12:00–14:00 | Allowed: back-to-back bookings are fine. |

As `admin`: reject without a reason (refused), or block Seminar Hall A on 4 Aug (refused, lists the clashing event).

The full checklist is in [`docs/test_runsheet.md`](docs/test_runsheet.md).

---

## 4. The problem we solved

Campus events were coordinated through messages and spreadsheets, so there was no single, trustworthy record of which venue is booked, blocked or free.

| Problem in the brief | How the app addresses it |
|---|---|
| Conflicting venue requests | Overlap check against pending requests, confirmed events and blocks, before submission |
| Venues chosen without regard to capacity | Expected attendance checked against venue capacity |
| No visibility into request status | **My requests** shows each status and any rejection reason |
| Slow review and confirmation | Admin **Review queue**, oldest first |
| Venues stay unavailable after cancellation | Rejecting or cancelling frees the slot immediately |
| Maintenance and renovation | Admin **Venue blocks** make a venue unavailable for a period |
| Different stakeholders need different things | Public view, plus Requester and Admin logins with their own pages |

---

## 5. Stakeholders and what each can do

| Role | Who | Login | Pages and actions |
|---|---|---|---|
| **Attendee** | Students, staff, guests | None (default view) | **Upcoming events** (confirmed events), **Venue schedule**. Read-only. |
| **Requester** | Students, club leads, faculty, placement cell | Yes | **New request** (live checks), **My requests** (status, reasons, cancel own confirmed events), plus the public pages |
| **Admin** | Facilities / student affairs office | Yes | **Review queue** (approve, or reject with a reason), **All events** (cancel any confirmed event), **Venue blocks** (add/remove), **Venue schedule**, **Reset demo data** |

The reviewer and approver are one role (Admin), so there is a single review step.

---

## 6. Request lifecycle

```
                 all checks pass
 New request ─────────────────────► PENDING ──approve──► CONFIRMED ──cancel──► CANCELLED
      │                                │                                  (slot released)
      │ any check fails                └──reject (reason required)──► REJECTED
      ▼                                                               (final, slot released)
 Refused with every reason; nothing is saved
```

- **PENDING** and **CONFIRMED** hold the venue slot. **REJECTED** and **CANCELLED** release it.
- Only these three transitions exist; any other is refused (for example, cancelling a rejected request).
- A rejected request is closed. To change details, the requester submits a new request.
- A confirmed event is the same record as its request, with status CONFIRMED, so its whole history is in one place.

---

## 7. Business rules and where they live

Every rule is enforced in the `rules/` package, never in the UI.

| # | Business condition (from the brief) | How it is enforced | Code | Tests |
|---|---|---|---|---|
| 1 | Event has a start, end and venue | All required; end must be after start | `rules/validation.py` `check_request` | T6 |
| 2 | No overlapping commitments on a venue | Overlap with PENDING or CONFIRMED requests is refused | `validation.booking_conflicts` | T2, T7 |
| 3 | Conflicts prevented before submission | Live check in the form; re-checked inside the write lock on submit | `validate_request`, `workflow.submit_request` | T2, UI tests |
| 4 | Venues can be unavailable | Admin venue blocks; overlap with a block is refused | `rules/venues.py`, `validation.block_conflicts` | T4, venue tests |
| 5 | Review before confirmation | New requests are PENDING; only Admin can approve | `workflow.approve`, `models.TRANSITIONS` | T1, T9 |
| 6 | Rejection closes the request and frees the venue | REJECTED is final and ignored by overlap checks; reason required | `workflow.reject` | T8 |
| 7 | An appropriate user can cancel | Requester (own events) or Admin (any) | `workflow._transition` | T1, cancel tests |
| 8 | Cancelling frees the venue | CANCELLED is ignored by overlap checks | `validation.booking_conflicts` | T1 |
| 9 | No partial/split bookings or alternative suggestions | Not built, by design | — | — |
| 10 | Clear reason when a request cannot proceed | Every refusal lists all reasons in plain language | `models.failure` | all failure tests |

**Overlap rule:** two bookings clash when `new_start < existing_end and new_end > existing_start`. Back-to-back bookings (10:00–12:00 then 12:00–14:00) do not clash.

---

## 8. Architecture

A layered, single-process app. Each layer only calls the one below it.

```
 Browser
    │
 app.py + ui/        Streamlit pages: collect input, show results. No rules, no file access.
    │
 rules/              All business rules: validation, conflicts, roles, transitions.
    │                Every write returns Result(ok, message, id).
 db/                 JSON file storage: lock, load, atomic save, seed data.
    │
 data/events.json
```

**How a write works** (for example, submitting a request):

1. The UI collects the form and calls `rules.submit_request(store, user_id, ...)`.
2. `rules` opens `store.transaction()`: takes the lock and loads the current data from disk.
3. It checks the role, then every validation rule, collecting **all** failure reasons.
4. If any check fails, it returns `Result(ok=False, message=...)` and nothing is written.
5. Otherwise it adds the request as PENDING; the transaction saves the file atomically (write to a temp file, then rename).
6. The UI shows the message and refreshes.

**Why this is safe:** the check and the write happen under one lock, so two people submitting the same slot at the same moment cannot both succeed. The lock is shared by every session in the server process.

---

## 9. Project structure

```
campus-events/
├── app.py                 Entry point: theme, login/logout, role-based navigation
├── auth.py                Password hashing (salted PBKDF2, standard library)
├── rules/                 Business rules (no UI code)
│   ├── __init__.py        Public API, re-exported for `import rules`
│   ├── models.py          Statuses, roles, event types, TRANSITIONS table, Result, date helpers
│   ├── validation.py      check_request, overlap and conflict detection
│   ├── workflow.py        submit_request, approve, reject, cancel, _transition
│   ├── venues.py          add_block, remove_block
│   └── queries.py         Read-only views for the UI, authenticate
├── db/                    Storage (no business decisions)
│   ├── connection.py      Store: JSON file, shared lock, transactions, atomic writes
│   ├── repository.py      find, next_id, now
│   └── seed.py            Initial campus data and staff accounts; `python -m db.seed --reset`
├── ui/                    Streamlit pages
│   ├── attendee.py        Public: confirmed events, venue schedule
│   ├── requester.py       New request (live checks), my requests
│   ├── admin.py           Review queue, all events, venue blocks
│   ├── components.py      Shared widgets: request card, pickers, schedule table, messages
│   └── theme.py           Loads the design system CSS; status chips
├── design-system/         Team design system (tokens, components, Streamlit overrides)
├── .streamlit/config.toml Streamlit theme matching the design system
├── tests/                 pytest suite (see Testing)
├── docs/
│   ├── plan.md            Original requirements and design plan (and what changed)
│   ├── test_runsheet.md   Manual demo checklist
│   └── pitch/             Two-slide consulting pitch
├── requirements.txt       streamlit, pytest (pinned versions)
└── pytest.ini
```

---

## 10. Data model

One JSON document in `data/events.json` with four lists. Dates are stored as `"YYYY-MM-DD HH:MM"` (campus local time), which sort and compare correctly as text.

```jsonc
{
  "users":    [{ "id": 1, "name": "Admin", "username": "admin", "role": "ADMIN",
                 "password_hash": "<salt>$<hash>" }],
  "venues":   [{ "id": 1, "name": "Seminar Hall A", "type": "Seminar Hall", "capacity": 120 }],
  "blocks":   [{ "id": 1, "venue_id": 3, "start": "2026-08-04 09:00", "end": "2026-08-04 18:00",
                 "reason": "Renovation", "created_by": 1 }],
  "requests": [{ "id": 1, "title": "AI Workshop", "event_type": "Technical Workshop",
                 "requester_id": 2, "venue_id": 1, "attendance": 100,
                 "start": "2026-08-04 10:00", "end": "2026-08-04 12:00",
                 "status": "CONFIRMED",          // PENDING | CONFIRMED | REJECTED | CANCELLED
                 "decision_reason": null,        // rejection or cancellation reason
                 "decided_by": 1,                // user who last changed the status
                 "created_at": "...", "updated_at": "..." }]
}
```

Event types: Technical Workshop, Hackathon, Placement Session, Club Activity, Cultural Programme, Student Competition (`rules/models.py`).

---

## 11. Rules API (for developers)

Everything the UI needs is available as `import rules`. Every write returns `Result(ok: bool, message: str, id: int | None)`; on failure, `message` lists every reason.

| Function | Who may call | What it does |
|---|---|---|
| `validate_request(store, title, event_type, venue_id, start, end, attendance)` | Anyone | Returns a list of reasons the request would fail (empty = valid). Saves nothing. |
| `submit_request(store, user_id, title, event_type, venue_id, start, end, attendance)` | Requester | Validates again under the lock; saves as PENDING |
| `approve(store, user_id, request_id)` | Admin | PENDING → CONFIRMED (re-checks conflicts) |
| `reject(store, user_id, request_id, reason)` | Admin | PENDING → REJECTED; reason required |
| `cancel(store, user_id, request_id, reason=None)` | Requester (own) / Admin | CONFIRMED → CANCELLED |
| `add_block(store, user_id, venue_id, start, end, reason)` | Admin | Blocks a venue; refused if it overlaps a pending/confirmed booking |
| `remove_block(store, user_id, block_id)` | Admin | Removes a block |
| `authenticate(store, username, password)` | Anyone | Returns the user (without password hash) or `None` |
| `get_user`, `list_users`, `list_venues`, `list_requests(requester_id=, status=, venue_id=)`, `pending_queue`, `list_blocks`, `venue_schedule(store, venue_id)` | UI | Read-only views |

`start` and `end` accept a `datetime` or a `"YYYY-MM-DD HH:MM"` string. Get a store with `from db import Store; store = Store()`.

---

## 12. Authentication

**Why we built it** (the brief makes login optional): approving, rejecting and cancelling change what everyone else can book, so those actions must be tied to a real person and role. Attendees only read public information, so they need no account and the landing page has no barrier.

- Passwords are stored only as salted PBKDF2-SHA256 hashes (`auth.py`); a test checks no plain password appears in the data file.
- A failed login shows a generic "Invalid username or password".
- The logged-in user id lives in Streamlit's server-side session state, never in the browser.
- **Defence in depth:** the UI hides actions a role cannot use, and `rules/` re-checks the role and ownership on every write.

---

## 13. Design system

The UI follows the team design system in `design-system/` (monochrome, editorial; see its README).

- `ui/theme.py` injects `tokens.css` and `streamlit.css` unchanged, plus a few app-specific styles built only from its tokens: status chips (outlined pills), monochrome alerts, sidebar brand.
- `.streamlit/config.toml` sets matching theme values: black primary, hairline borders, 6px cards, pill buttons.
- Following its rules, there are no accent colours or emoji; only key actions (Submit, Log in, Add block) use the filled black button.

---

## 14. Testing

```bash
python -m pytest -q        # 47 tests, about 10 seconds
```

| File | Covers |
|---|---|
| `tests/test_validation.py` | T2 overlap, T3 back-to-back, T4 renovation block, T5 capacity, T6 time order; all reasons reported together; bad attendance, venue and date-time; multi-day events; a refused request leaves the file untouched |
| `tests/test_workflow.py` | T7 pending holds slot, T8 rejection frees slot and is final; reason required; T9 role and transition refusals; cancel own vs any; login success/failure; no plain-text passwords; persistence; queue order |
| `tests/test_venues.py` | T10 block over an event refused; block add/remove; Admin only; venue schedule |
| `tests/test_flow_e2e.py` | T1 full lifecycle through `rules`; then the **real Streamlit app** driven headlessly with `streamlit.testing.v1.AppTest`: submit → approve → public view → cancel, conflict warning with Submit disabled, capacity warning, reject needs a reason, block refused, public landing page, wrong password, requester sees only own pages, logout |

Each test gets a fresh seeded data file in a temporary folder (`tests/conftest.py`), so tests never touch `data/events.json`.

Manual checks before the demo: [`docs/test_runsheet.md`](docs/test_runsheet.md).

---

## 15. Assumptions

1. Back-to-back bookings are allowed (strict overlap).
2. Pending requests and confirmed events hold the venue; rejected and cancelled ones release it.
3. Multi-day events are allowed (hackathons often run overnight).
4. Past dates are not blocked, because the brief's seed data (Aug 2026) is already in the past.
5. Venue suitability is checked by capacity only.
6. A rejection reason is mandatory; rejected requests are final.
7. Requesters cancel only their own confirmed events; the Admin can cancel any.
8. An Admin cannot block a venue over an existing pending/confirmed booking; the clashing bookings are listed so they can be resolved first, so nothing is cancelled silently.
9. Reviewer and approver are one role (Admin).
10. Login is local to the app (no campus SSO); accounts are seeded, with no sign-up or password reset.
11. Times are campus local time, minute precision.

---

## 16. Scope: built and excluded

**Built:** full request lifecycle; validation before submission with all reasons; venue blocks; role-based pages; public attendee view; staff login; persistence across restarts; automated rule and UI tests.

**Excluded by the brief:** partial bookings, split bookings, automatic alternative-venue suggestions.

**Excluded for time:** requester withdrawing a pending request; adding or editing venues in the UI (seeded venues only); notifications; calendar export; status history/audit log; matching event type to venue type.

---

## 17. Trade-offs

| Decision | Alternative | Why |
|---|---|---|
| JSON file | SQLite | No setup, readable during the demo; a lock plus atomic writes give the consistency needed at campus scale |
| Streamlit | Flask/FastAPI + frontend | Fastest Python UI in 90 minutes; less layout control |
| Live check **and** re-check on submit | Check only on submit | Users see problems as they type; the locked re-check still refuses a slot taken in the meantime |
| Report all reasons at once | Stop at first failure | Users fix everything in one go |
| Block cannot overlap bookings | Auto-cancel affected bookings | No event is cancelled silently; Admin resolves conflicts explicitly |
| One record per request/event | Separate requests and events | Whole history in one place; status filter instead of joins |
| Login for staff only | Login for everyone / no login | Protects state-changing actions without adding friction for attendees |

---

## 18. Known limitations

- Single server process: the lock protects sessions within one Streamlit server, not several servers sharing a file.
- No notifications, calendar export, venue editing or audit history.
- Seeded accounts only; no user management or password reset.
- Past dates can be booked (see assumption 4).
- No event-type-to-venue-type suitability check.

---

## 19. Next steps

1. Campus SSO instead of local accounts; roles from the university directory.
2. Move storage to a database (SQLite, then PostgreSQL) for multi-user scale.
3. Notifications on submit, approve, reject and cancel.
4. Calendar view and `.ics` export of confirmed events.
5. Audit log of every status change; utilisation analytics per venue.
6. Venue features (projector, lab PCs) and event-type matching; requester withdrawal of pending requests.

---

## 20. How AI was used

AI tools (Claude Code) were used to review the requirements, draft code, tests and documentation. The team directed the design and reviewed, ran and validated every output.

Examples where review changed the design:

- **Requirements review:** the AI flagged that our single-day-event assumption would break multi-day hackathons, so it was dropped. It also pointed out that capacity was our only suitability check (now documented as an assumption), and that a "venue availability finder" bonus would overlap with the brief's excluded alternative-venue suggestions.
- **Correctness:** the store re-reads data on every check and uses one lock shared across browser sessions, after reviewing how Streamlit reruns create new objects each time.
- **Validation:** every rule has a test, and the real UI is exercised headlessly, not just the functions.

<!-- Team: each member adds one AI suggestion they reviewed, corrected or rejected, and how they validated their part. -->

---

## 21. Consulting pitch

**Slide 1: Problem understanding**

- *Problem:* no single trustworthy record of venue bookings, so requests clash, stall and go unreviewed.
- *Stakeholders:* Requesters (students, clubs, faculty), Admin (facilities / student affairs), Attendees (everyone on campus).
- *Workflows prioritised:* request → review → confirm or reject → cancel; venue blocks; public view of confirmed events.
- *Key rules:* no overlapping holds; pending requests hold the slot; rejection and cancellation release it; capacity and blocks checked before submission; every refusal explains why.
- *Key assumptions:* back-to-back allowed, multi-day allowed, one Admin review step, staff-only login.
- *Scope for 90 minutes:* the complete lifecycle for three roles, done reliably, rather than many partial features.

**Slide 2: Solution and engineering decisions**

- *Approach:* layered Streamlit app; all rules in one `rules/` package; JSON storage with a shared lock and atomic writes.
- *Design decisions:* one status-transition table; validate live and again under the lock; report all reasons at once; blocks never silently cancel bookings.
- *Trade-offs:* JSON over a database for zero setup; Streamlit over a custom frontend for speed.
- *Testing:* 47 automated tests covering every rule and the real UI flows, plus a manual run sheet.
- *Limitations:* single-server, seeded accounts, no notifications.
- *Next:* SSO, database, notifications, calendar export, analytics.

---

## 22. Contributing

- **Where code goes:** business rules only in `rules/`; storage only in `db/`; pages only in `ui/`. The UI never reads the data file or decides a rule.
- **Adding a rule:** add the check in `rules/validation.py` (or the relevant module), return a plain-language reason, and add a test in `tests/`.
- **Adding a page:** write `page_x(user)` in the right `ui/` module, then add it to `PAGES` and `PAGE_FUNCS` in `app.py`.
- **Changing statuses:** edit `TRANSITIONS` in `rules/models.py`; all status changes go through `workflow._transition`.
- **Before pushing:** `python -m pytest -q` must pass. Make small commits with clear messages; each member commits their own work.

---

## 23. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: streamlit` | Activate the virtual environment, then `pip install -r requirements.txt` |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` |
| Data looks wrong or demo state is messy | `python -m db.seed --reset` |
| Login fails with the demo passwords | The data file is from an older version; reset it as above |
| Tests can't import `rules` | Run pytest from the `campus-events/` folder |
