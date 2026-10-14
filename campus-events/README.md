# Campus Event Management System

Request a campus venue, get it reviewed by an Admin, and keep venue availability accurate.

## Run

Prerequisite: Python 3.10+.

```bash
cd campus-events
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py            # opens http://localhost:8501
```

- Data lives in `data/events.json`, created and seeded with the brief's campus data on first run.
- Reset before a demo: `python -m db.seed --reset`, or **Reset demo data** in the sidebar (Admin only).
- Tests: `python -m pytest -q` (business rules + headless UI tests). Manual run sheet: `docs/test_runsheet.md`.

## Structure

Layered: `app.py` and `ui/` call `rules/` only; `rules/` alone uses `db/`.

| Path | Role |
|---|---|
| `app.py` | Entry point: page config, staff login, role-based navigation. |
| `ui/` | Streamlit pages: `requester.py`, `admin.py`, `attendee.py` (public), shared `components.py`, `theme.py`. No business rules. |
| `rules/` | All business rules. `models.py` (statuses, roles, allowed transitions, `Result`), `validation.py` (checks and overlap), `workflow.py` (submit, approve, reject, cancel), `venues.py` (blocks), `queries.py` (reads, login). No UI code. |
| `db/` | JSON file storage with a lock and atomic writes (`connection.py`), lookup helpers (`repository.py`), seed data (`seed.py`). |
| `auth.py` | Salted PBKDF2 password hashing (standard library). |
| `design-system/`, `.streamlit/config.toml` | Team design system, applied via `ui/theme.py`. |
| `tests/` | `test_validation.py` (T2–T6), `test_workflow.py` (T7–T9, login), `test_venues.py` (T10), `test_flow_e2e.py` (T1 + UI flows). |

## Roles and access

- **Attendee** (no login): the default view when anyone opens the portal. Confirmed events and venue schedules, read-only.
- **Requester** (staff login): new request with live checks, my requests, cancel own confirmed events.
- **Admin** (staff login): review queue (approve / reject with reason), all events (cancel any), venue blocks, reset demo data.

Demo logins (sidebar "Staff login"):

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |
| `asha` | `asha123` | Requester |
| `ravi` | `ravi123` | Requester |

**Why authentication was prioritised:** approving, rejecting and cancelling change what everyone else can book, so these actions must be tied to a real person and role (business conditions 5–8). Attendees only read public information, so they get no account, which keeps the landing page friction-free. Passwords are stored only as salted hashes. Roles are also re-checked in `rules/` on every write, so hiding a button is never the only protection.

## Request lifecycle

```
submit (all checks pass) -> PENDING --approve--> CONFIRMED --cancel--> CANCELLED
                                    \--reject (reason required)--> REJECTED (final)
```

PENDING and CONFIRMED hold the venue slot; REJECTED and CANCELLED release it. Any other transition is refused.

## Assumptions

1. Back-to-back bookings are allowed (strict overlap: `start < other_end and end > other_start`).
2. Pending requests and confirmed events hold the venue; rejected and cancelled ones release it.
3. Multi-day events are allowed.
4. Past dates are not blocked, because the brief's seed data (Aug 2026) is already in the past.
5. Venue suitability is checked by capacity only.
6. A rejection reason is mandatory; rejected requests are final.
7. Requesters cancel only their own confirmed events; the Admin can cancel any.
8. An Admin cannot block a venue over an existing pending/confirmed booking; the clashes are listed to resolve first.
9. Reviewer and approver are one role (Admin).
10. Login is local to the app (no campus SSO); accounts are seeded, with no sign-up or password reset.

## Trade-offs

- **JSON file instead of SQLite:** zero setup and readable during the demo; a lock plus atomic writes give the consistency we need at campus scale. A database would be the next step for many concurrent users.
- **Live checks plus re-check on submit:** the form shows every problem as you type and disables Submit, and `submit_request` validates again inside the write lock, so a slot taken in the meantime is still refused.
- **Streamlit:** fastest Python UI to build in 90 minutes; less layout control than a custom frontend.

## Known limitations

- Single-process local app; not built for many simultaneous users.
- No notifications, calendar export or venue editing.
- Seeded accounts only; no user management.
