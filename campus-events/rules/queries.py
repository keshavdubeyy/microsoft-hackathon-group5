"""Read-only views for the UI, and staff login. Nothing here changes data."""
import logging

from auth import DUMMY_HASH, verify_password
from db import find
from rules.models import ACTIVE, CONFIRMED, PENDING

log = logging.getLogger("rules")


def _public(user):
    return {k: v for k, v in user.items() if k != "password_hash"}


def authenticate(store, username, password):
    """Staff login. Returns the user (without password hash) or None."""
    username = str(username or "").strip().lower()
    user = next((u for u in store.read()["users"] if u["username"] == username), None)
    matches = verify_password(str(password or ""), user["password_hash"] if user else DUMMY_HASH)
    if user is None or not matches:
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


def venue_schedule(store, venue_id, public=False):
    """Everything occupying a venue: confirmed events, pending holds and blocks.

    public=True is the attendee view: pending requests are not approved yet,
    so only the held time is shown, not the title.
    """
    rows = [
        {"kind": "Event" if r["status"] == CONFIRMED else "Pending hold",
         "title": "Awaiting review" if public and r["status"] == PENDING else r["title"],
         "start": r["start"], "end": r["end"], "ref": r["id"]}
        for r in list_requests(store, venue_id=venue_id)
        if r["status"] in ACTIVE
    ]
    rows += [
        {"kind": "Blocked", "title": b["reason"], "start": b["start"], "end": b["end"], "ref": b["id"]}
        for b in list_blocks(store, venue_id=venue_id)
    ]
    return sorted(rows, key=lambda row: row["start"])
