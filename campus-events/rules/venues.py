"""Venue blocks for maintenance, renovation or other restrictions (business condition 4)."""
import logging

from db import find, next_id
from rules.models import ADMIN, Result, describe_window, failure
from rules.validation import block_conflicts, booking_conflicts, parse_window

log = logging.getLogger("rules")


def add_block(store, user_id, venue_id, start, end, reason):
    """Admin blocks a venue. Every reason it cannot be added is returned together.

    Refused if it would overlap a pending/confirmed booking, or an existing
    block on the same venue (which also stops a double-click saving it twice).
    """
    with store.transaction() as data:
        user = find(data["users"], user_id)
        if user is None or user["role"] != ADMIN:
            return Result(False, "Only an Admin can block venues.")

        reasons = []
        venue = find(data["venues"], venue_id)
        if venue is None:
            reasons.append("Selected venue does not exist.")
        reason = str(reason or "").strip()
        if not reason:
            reasons.append("A block reason is required (e.g. Maintenance, Renovation).")
        time_reasons, start_s, end_s = parse_window(start, end)
        reasons.extend(time_reasons)
        if venue and not time_reasons:
            reasons.extend(block_conflicts(data, venue_id, start_s, end_s))
            # A7: never cancel bookings silently; the admin resolves them first.
            reasons.extend(booking_conflicts(data, venue_id, start_s, end_s))
        if reasons:
            return failure("Block cannot be added:", reasons)

        block = {
            "id": next_id(data["blocks"]),
            "venue_id": venue_id,
            "start": start_s,
            "end": end_s,
            "reason": reason,
            "created_by": user_id,
        }
        data["blocks"].append(block)
        log.info("user=%s added block #%s on venue %s", user["name"], block["id"], venue_id)
        return Result(True, f"{venue['name']} blocked for {describe_window(start_s, end_s)}.", block["id"])


def remove_block(store, user_id, block_id):
    with store.transaction() as data:
        user = find(data["users"], user_id)
        if user is None or user["role"] != ADMIN:
            return Result(False, "Only an Admin can remove venue blocks.")
        block = find(data["blocks"], block_id)
        if block is None:
            return Result(False, f"Block #{block_id} does not exist.")
        data["blocks"].remove(block)
        log.info("user=%s removed block #%s", user["name"], block_id)
        return Result(True, "Venue block removed.", block_id)
