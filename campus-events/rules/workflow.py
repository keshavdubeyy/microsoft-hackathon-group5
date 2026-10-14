"""Request lifecycle: submit, approve, reject, cancel (business conditions 5-8)."""
import logging

from db import find, next_id, now
from rules.models import (
    CANCELLED, CONFIRMED, PENDING, REJECTED, REQUESTER, TRANSITIONS, Result, failure,
)
from rules.validation import check_request, find_conflicts

log = logging.getLogger("rules")


def submit_request(store, user_id, title, event_type, venue_id, start, end, attendance):
    """Validate and, only if everything passes, save as PENDING (holds the slot)."""
    with store.transaction() as data:
        user = find(data["users"], user_id)
        if user is None or user["role"] != REQUESTER:
            return Result(False, "Only a Requester can submit event requests.")

        reasons, start_s, end_s = check_request(data, title, event_type, venue_id, start, end, attendance)
        if reasons:
            return failure("Request cannot be submitted:", reasons)

        ts = now()
        request = {
            "id": next_id(data["requests"]),
            "title": str(title).strip(),
            "event_type": event_type,
            "requester_id": user_id,
            "venue_id": venue_id,
            "attendance": attendance,
            "start": start_s,
            "end": end_s,
            "status": PENDING,
            "decision_reason": None,
            "decided_by": None,
            "created_at": ts,
            "updated_at": ts,
        }
        data["requests"].append(request)
        log.info("user=%s submitted request #%s", user["name"], request["id"])
        return Result(True, f"Request #{request['id']} submitted and is pending review.", request["id"])


def _refusal(data, user_id, request_id, to_status):
    """Why this user may not move this request to to_status, or None if allowed."""
    user = find(data["users"], user_id)
    request = find(data["requests"], request_id)
    if user is None:
        return Result(False, "Unknown user.")
    if request is None:
        return Result(False, f"Request #{request_id} does not exist.")

    from_status = request["status"]
    allowed_roles = TRANSITIONS.get((from_status, to_status))
    if allowed_roles is None:
        return Result(
            False, f"Cannot change a {from_status.lower()} request to {to_status.lower()}."
        )
    if user["role"] not in allowed_roles:
        return Result(False, f"A {user['role'].lower()} is not allowed to do this.")
    if user["role"] == REQUESTER and request["requester_id"] != user_id:
        return Result(False, "You can only cancel your own events.")
    return None


def _transition(data, user_id, request_id, to_status, reason=None):
    """The single place where a request's status changes."""
    refused = _refusal(data, user_id, request_id, to_status)
    if refused is not None:
        return refused

    user = find(data["users"], user_id)
    request = find(data["requests"], request_id)
    from_status = request["status"]
    request["status"] = to_status
    request["decision_reason"] = reason
    request["decided_by"] = user_id
    request["updated_at"] = now()
    log.info("user=%s request #%s %s -> %s", user["name"], request_id, from_status, to_status)
    return Result(True, f"Request #{request_id} is now {to_status.lower()}.", request_id)


def approve(store, user_id, request_id):
    """PENDING -> CONFIRMED. Checks the role first, then re-checks conflicts as a safety net."""
    with store.transaction() as data:
        refused = _refusal(data, user_id, request_id, CONFIRMED)
        if refused is not None:
            return refused

        request = find(data["requests"], request_id)
        reasons = find_conflicts(
            data, request["venue_id"], request["start"], request["end"], exclude_id=request_id
        )
        if reasons:
            return failure("Cannot approve:", reasons)
        return _transition(data, user_id, request_id, CONFIRMED)


def reject(store, user_id, request_id, reason):
    """PENDING -> REJECTED. A reason is mandatory; the slot is released."""
    reason = str(reason or "").strip()
    with store.transaction() as data:
        refused = _refusal(data, user_id, request_id, REJECTED)
        if refused is not None:
            return refused
        if not reason:
            return Result(False, "A rejection reason is required.")
        return _transition(data, user_id, request_id, REJECTED, reason)


def cancel(store, user_id, request_id, reason=None):
    """CONFIRMED -> CANCELLED. Requester (own event) or Admin; the slot is released."""
    with store.transaction() as data:
        return _transition(data, user_id, request_id, CANCELLED, str(reason or "").strip() or None)
