"""Business rules for the Campus Event Management System.

Every business condition from the brief is enforced in this package, and
nowhere else. No UI code: the Streamlit app calls these functions and shows
the Result. Every write returns Result(ok, message, id).
"""
from rules.models import (
    ACTIVE, ADMIN, CANCELLED, CONFIRMED, DT_FORMAT, EVENT_TYPES, PENDING, REJECTED,
    REQUESTER, TRANSITIONS, Result, describe_window, to_dt_str,
)
from rules.admin import reset_demo_data
from rules.queries import (
    authenticate, get_user, list_blocks, list_requests, list_users, list_venues,
    pending_queue, venue_schedule,
)
from rules.validation import BLOCK_REASON_MAX, TITLE_MAX, find_conflicts, overlaps, validate_request
from rules.venues import add_block, remove_block
from rules.workflow import REASON_MAX, approve, cancel, reject, submit_request
