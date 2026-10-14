"""Venue blocks for maintenance, renovation or other restrictions (business condition 4)."""
import logging

from db import find, next_id
from rules.models import ADMIN, Result, describe_window, failure, to_dt_str
from rules.validation import booking_conflicts

log = logging.getLogger("rules")


def add_block(store, user_id, venue_id, start, end, reason):
    """Admin blocks a venue. Refused if it would overlap a pending/confirmed booking."""
    with store.transaction() as data:
        user = find(data["users"], user_id)
        if user is None or user["role"] != ADMIN:
            return Result(False, "Only an Admin can block venues.")

        reasons = []
        if find(data["venues"], venue_id) is None:
            reasons.append("Selected venue does not exist.")
        if not str(reason or "").strip():
            reasons.append("A block reason is required (e.g. Maintenance, Renovation).")
        try:
            start_s, end_s = to_dt_str(start), to_dt_str(end)
        except ValueError:
            reasons.append("Start and end must be valid date-times (YYYY-MM-DD HH:MM).")
            return failure("Block cannot be added:", reasons)
        if end_s <= start_s:
            reasons.append("End date-time must be after start date-time.")
        elif not reasons:
            # A7: never cancel bookings silently; the admin resolves them first.
            reasons.extend(booking_conflicts(data, venue_id, start_s, end_s))
        if reasons:
            return failure("Block cannot be added:", reasons)

        block = {
            "id": next_id(data["blocks"]),
            "venue_id": venue_id,
            "start": start_s,
            "end": end_s,
            "reason": reason.strip(),
            "created_by": user_id,
        }
        data["blocks"].append(block)
        log.info("user=%s added block #%s on venue %s", user["name"], block["id"], venue_id)
        return Result(True, f"Venue blocked for {describe_window(start_s, end_s)}.", block["id"])


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
