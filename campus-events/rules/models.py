"""The shared contract: statuses, roles, allowed transitions and Result.

Lifecycle:  PENDING -> CONFIRMED -> CANCELLED
            PENDING -> REJECTED   (closed for good)
PENDING and CONFIRMED hold the venue slot; REJECTED and CANCELLED release it.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

PENDING, CONFIRMED, REJECTED, CANCELLED = "PENDING", "CONFIRMED", "REJECTED", "CANCELLED"
ACTIVE = (PENDING, CONFIRMED)  # statuses that hold a venue slot

ADMIN, REQUESTER = "ADMIN", "REQUESTER"  # staff roles; attendees are anonymous visitors

EVENT_TYPES = [
    "Technical Workshop",
    "Hackathon",
    "Placement Session",
    "Club Activity",
    "Cultural Programme",
    "Student Competition",
]

DT_FORMAT = "%Y-%m-%d %H:%M"

# The only allowed status changes, and which roles may make them.
# Requesters may cancel only their own events (checked in workflow._transition).
TRANSITIONS = {
    (PENDING, CONFIRMED): {ADMIN},
    (PENDING, REJECTED): {ADMIN},
    (CONFIRMED, CANCELLED): {ADMIN, REQUESTER},
}


@dataclass
class Result:
    ok: bool
    message: str
    id: Optional[int] = None


def failure(heading, reasons):
    return Result(False, heading + "\n" + "\n".join(f"- {r}" for r in reasons))


def to_dt_str(value):
    """Normalise a datetime or 'YYYY-MM-DD HH:MM' string. Raises ValueError."""
    if isinstance(value, datetime):
        return value.strftime(DT_FORMAT)
    return datetime.strptime(str(value).strip(), DT_FORMAT).strftime(DT_FORMAT)


def describe_window(start, end):
    """'4 Aug 2026, 10:00-12:00', or both dates for multi-day windows."""
    s = datetime.strptime(start, DT_FORMAT)
    e = datetime.strptime(end, DT_FORMAT)
    if s.date() == e.date():
        return f"{s.day} {s:%b %Y}, {s:%H:%M}–{e:%H:%M}"
    return f"{s.day} {s:%b %Y} {s:%H:%M} – {e.day} {e:%b %Y} {e:%H:%M}"
