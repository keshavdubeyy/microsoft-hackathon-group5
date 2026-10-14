"""Request validation and conflict detection (business conditions 1-4 and 10)."""
from db import find
from rules.models import ACTIVE, CONFIRMED, EVENT_TYPES, describe_window, to_dt_str


def overlaps(start_a, end_a, start_b, end_b):
    """Strict overlap, so back-to-back bookings (10-12 then 12-14) are allowed.

    Fixed-width 'YYYY-MM-DD HH:MM' strings compare correctly as text.
    """
    return start_a < end_b and end_a > start_b


def booking_conflicts(data, venue_id, start, end, exclude_id=None):
    """Reasons why PENDING/CONFIRMED requests clash with this window."""
    reasons = []
    for r in data["requests"]:
        if (
            r["venue_id"] == venue_id
            and r["status"] in ACTIVE
            and r["id"] != exclude_id
            and overlaps(start, end, r["start"], r["end"])
        ):
            kind = "a confirmed event" if r["status"] == CONFIRMED else "a pending request"
            reasons.append(
                f"Clashes with {kind} '{r['title']}' (#{r['id']}) on {describe_window(r['start'], r['end'])}."
            )
    return reasons


def block_conflicts(data, venue_id, start, end):
    """Reasons why venue blocks (maintenance, renovation...) clash with this window."""
    return [
        f"Venue is unavailable ({b['reason']}) on {describe_window(b['start'], b['end'])}."
        for b in data["blocks"]
        if b["venue_id"] == venue_id and overlaps(start, end, b["start"], b["end"])
    ]


def find_conflicts(data, venue_id, start, end, exclude_id=None):
    return block_conflicts(data, venue_id, start, end) + booking_conflicts(
        data, venue_id, start, end, exclude_id
    )


def check_request(data, title, event_type, venue_id, start, end, attendance):
    """Every reason the request would fail (empty list = valid).

    Returns (reasons, start_str, end_str) so callers reuse the parsed times.
    """
    reasons = []
    if not str(title or "").strip():
        reasons.append("Event title is required.")
    if event_type not in EVENT_TYPES:
        reasons.append(f"Event type must be one of: {', '.join(EVENT_TYPES)}.")

    venue = find(data["venues"], venue_id)
    if venue is None:
        reasons.append("Selected venue does not exist.")

    if isinstance(attendance, bool) or not isinstance(attendance, int) or attendance < 1:
        reasons.append("Expected attendance must be a whole number of at least 1.")
    elif venue and attendance > venue["capacity"]:
        reasons.append(
            f"Expected attendance {attendance} exceeds {venue['name']} capacity of {venue['capacity']}."
        )

    try:
        start_s, end_s = to_dt_str(start), to_dt_str(end)
    except ValueError:
        reasons.append("Start and end must be valid date-times (YYYY-MM-DD HH:MM).")
        return reasons, None, None

    if end_s <= start_s:
        reasons.append("End date-time must be after start date-time.")
    elif venue:
        reasons.extend(find_conflicts(data, venue_id, start_s, end_s))
    return reasons, start_s, end_s


def validate_request(store, title, event_type, venue_id, start, end, attendance):
    """Read-only check for live feedback in the form. Returns a list of reasons."""
    reasons, _, _ = check_request(store.read(), title, event_type, venue_id, start, end, attendance)
    return reasons
