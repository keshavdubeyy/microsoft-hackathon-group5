"""Read-only views for the UI, and staff login. Nothing here changes data."""
import logging

from auth import verify_password
from datetime import datetime

from db import find
from rules.models import ACTIVE, CONFIRMED, DT_FORMAT, PENDING, REJECTED
from rules.validation import find_conflicts

log = logging.getLogger("rules")


def _public(user):
    return {k: v for k, v in user.items() if k != "password_hash"}


def authenticate(store, username, password):
    """Staff login. Returns the user (without password hash) or None."""
    username = str(username or "").strip().lower()
    user = next((u for u in store.read()["users"] if u["username"] == username), None)
    if user is None or not verify_password(str(password or ""), user["password_hash"]):
        log.info("failed login for username=%r", username)
        return None
    log.info("user=%s logged in", user["name"])
    return _public(user)


def get_user(store, user_id):
    user = find(store.read()["users"], user_id)
    return _public(user) if user else None


def list_users(store):
    return [_public(u) for u in store.read()["users"]]


def list_venues(store):
    return store.read()["venues"]


def list_requests(store, requester_id=None, status=None, venue_id=None):
    """Requests with venue and requester names attached, sorted by start time."""
    data = store.read()
    venues = {v["id"]: v["name"] for v in data["venues"]}
    users = {u["id"]: u["name"] for u in data["users"]}
    rows = []
    for r in data["requests"]:
        if requester_id is not None and r["requester_id"] != requester_id:
            continue
        if status is not None and r["status"] != status:
            continue
        if venue_id is not None and r["venue_id"] != venue_id:
            continue
        rows.append({**r, "venue_name": venues.get(r["venue_id"]), "requester_name": users.get(r["requester_id"])})
    return sorted(rows, key=lambda r: r["start"])


def pending_queue(store):
    """Pending requests, oldest submission first."""
    return sorted(list_requests(store, status=PENDING), key=lambda r: (r["created_at"], r["id"]))


def list_blocks(store, venue_id=None):
    data = store.read()
    venues = {v["id"]: v["name"] for v in data["venues"]}
    return sorted(
        ({**b, "venue_name": venues.get(b["venue_id"])} for b in data["blocks"]
         if venue_id is None or b["venue_id"] == venue_id),
        key=lambda b: b["start"],
    )


def venue_schedule(store, venue_id):
    """Everything occupying a venue: confirmed events, pending holds and blocks."""
    rows = [
        {"kind": "Event" if r["status"] == CONFIRMED else "Pending hold",
         "title": r["title"], "start": r["start"], "end": r["end"], "ref": r["id"]}
        for r in list_requests(store, venue_id=venue_id)
        if r["status"] in ACTIVE
    ]
    rows += [
        {"kind": "Blocked", "title": b["reason"], "start": b["start"], "end": b["end"], "ref": b["id"]}
        for b in list_blocks(store, venue_id=venue_id)
    ]
    return sorted(rows, key=lambda row: row["start"])


def search_requests(store, text="", statuses=None):
    """Requests whose title, type, venue, requester or id contains `text` (case-insensitive).

    `statuses` limits the result to those statuses; None or empty means all.
    """
    needle = str(text or "").strip().lower()
    rows = []
    for r in list_requests(store):
        if statuses and r["status"] not in statuses:
            continue
        haystack = " ".join(
            str(r[k]) for k in ("id", "title", "event_type", "venue_name", "requester_name")
        ).lower()
        if needle in haystack:
            rows.append(r)
    return rows


def review_details(store, request_id):
    """Everything an Admin needs to decide on a request, or None if it does not exist."""
    data = store.read()
    request = find(data["requests"], request_id)
    if request is None:
        return None
    venue = find(data["venues"], request["venue_id"])
    hours = (
        datetime.strptime(request["end"], DT_FORMAT) - datetime.strptime(request["start"], DT_FORMAT)
    ).total_seconds() / 3600
    day = request["start"][:10]
    same_day = [
        row for row in venue_schedule(store, request["venue_id"])
        if row["start"][:10] <= day <= row["end"][:10]
        and not (row["kind"] == "Pending hold" and row["ref"] == request_id)
    ]
    history = [r for r in data["requests"]
               if r["requester_id"] == request["requester_id"] and r["id"] != request_id]
    return {
        "capacity": venue["capacity"],
        "venue_type": venue["type"],
        "fill_percent": round(100 * request["attendance"] / venue["capacity"]),
        "duration_hours": round(hours, 1),
        "submitted_at": request["created_at"],
        # Empty means safe to approve.
        "conflicts": find_conflicts(
            data, request["venue_id"], request["start"], request["end"], exclude_id=request_id
        ),
        "same_day_schedule": same_day,
        "requester_confirmed": sum(r["status"] == CONFIRMED for r in history),
        "requester_rejected": sum(r["status"] == REJECTED for r in history),
    }
