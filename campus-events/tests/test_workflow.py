"""Lifecycle, roles and login (T7-T9)."""
import json

import pytest

import rules
from db import Store

ADMIN, ASHA, RAVI, UNKNOWN_USER = 1, 2, 3, 99
MAIN_AUD, AMPHI, INNOV_LAB = 2, 4, 5
SEMINAR_EVENT, LAB_EVENT = 1, 2  # seeded confirmed events (Asha, Ravi)


def _request(store, request_id):
    return next(r for r in rules.list_requests(store) if r["id"] == request_id)


def _add_block_directly(store):
    """A clash that appears after submission, bypassing add_block's own checks."""
    with store.transaction() as data:
        data["blocks"].append({"id": 99, "venue_id": MAIN_AUD, "start": "2026-08-05 09:00",
                               "end": "2026-08-05 11:00", "reason": "Maintenance", "created_by": ADMIN})


# ---- T7-T8: pending holds the slot; rejection releases it

def test_t7_pending_request_holds_the_slot(submit):
    assert submit().ok
    second = submit(user=RAVI)
    assert not second.ok
    assert "pending request" in second.message


def test_t8_rejection_releases_slot_and_is_final(store, submit, status_of):
    first = submit()
    assert rules.reject(store, ADMIN, first.id, "Clashes with exams").ok
    assert status_of(first.id) == rules.REJECTED

    assert submit(user=RAVI).ok
    # Rejected is closed: cannot be approved or cancelled afterwards.
    assert not rules.approve(store, ADMIN, first.id).ok
    assert not rules.cancel(store, ADMIN, first.id).ok


def test_rejection_requires_reason(store, submit, status_of):
    res = submit()
    assert not rules.reject(store, ADMIN, res.id, "   ").ok
    assert status_of(res.id) == rules.PENDING


# ---- T9: roles and transitions

def test_t9_requester_cannot_approve_or_reject(store, submit, status_of):
    res = submit()
    assert not rules.approve(store, ASHA, res.id).ok
    assert not rules.reject(store, RAVI, res.id, "no").ok
    assert status_of(res.id) == rules.PENDING


def test_t9_cannot_cancel_rejected_or_pending(store, submit):
    res = submit()
    assert not rules.cancel(store, ASHA, res.id).ok  # pending -> cancelled not allowed
    rules.reject(store, ADMIN, res.id, "Not suitable")
    assert "Cannot change a rejected request" in rules.cancel(store, ASHA, res.id).message


def test_requester_cancels_only_own_event(store):
    assert not rules.cancel(store, RAVI, SEMINAR_EVENT).ok  # Asha's event
    assert rules.cancel(store, ASHA, SEMINAR_EVENT).ok


def test_admin_cancels_any_event_and_slot_frees(store, submit):
    assert rules.cancel(store, ADMIN, LAB_EVENT, "Speaker unavailable").ok
    res = submit(venue=INNOV_LAB, start="2026-08-06 14:00", end="2026-08-06 17:00", attendance=40)
    assert res.ok, res.message


def test_only_requesters_submit(submit):
    assert not submit(user=ADMIN).ok
    assert not submit(user=UNKNOWN_USER).ok


# ---- approve and its safety net

def test_admin_approves_and_confirmed_event_holds_slot(store, submit, status_of):
    res = submit()
    assert rules.approve(store, ADMIN, res.id).ok
    assert status_of(res.id) == rules.CONFIRMED
    second = submit(user=RAVI)
    assert not second.ok
    assert "confirmed event" in second.message


def test_approve_rechecks_conflicts(store, submit, status_of):
    res = submit()
    _add_block_directly(store)
    result = rules.approve(store, ADMIN, res.id)
    assert not result.ok
    assert "Maintenance" in result.message
    assert status_of(res.id) == rules.PENDING


def test_role_is_checked_before_conflicts_and_reason(store, submit):
    res = submit()
    _add_block_directly(store)
    assert "requester is not allowed" in rules.approve(store, RAVI, res.id).message
    assert "requester is not allowed" in rules.reject(store, RAVI, res.id, "").message


# ---- invalid transitions and bad input

def test_repeat_transitions_refused(store, status_of):
    assert "Cannot change a confirmed request" in rules.approve(store, ADMIN, SEMINAR_EVENT).message
    assert "Cannot change a confirmed request" in rules.reject(store, ADMIN, SEMINAR_EVENT, "Late").message
    assert rules.cancel(store, ADMIN, SEMINAR_EVENT).ok
    assert "Cannot change a cancelled request" in rules.cancel(store, ADMIN, SEMINAR_EVENT).message
    assert status_of(SEMINAR_EVENT) == rules.CANCELLED


def test_unknown_request_or_user_refused(store):
    for res in (rules.approve(store, ADMIN, 999),
                rules.reject(store, ADMIN, 999, "No"),
                rules.cancel(store, ADMIN, 999)):
        assert not res.ok
        assert "does not exist" in res.message
    assert rules.approve(store, UNKNOWN_USER, SEMINAR_EVENT).message == "Unknown user."


def test_refused_transitions_leave_file_untouched(store, submit):
    res = submit()
    with open(store.path, encoding="utf-8") as f:
        before = f.read()
    rules.approve(store, ASHA, res.id)          # wrong role
    rules.reject(store, ADMIN, res.id, "  ")    # no reason
    rules.cancel(store, ASHA, res.id)           # pending cannot be cancelled
    rules.cancel(store, RAVI, SEMINAR_EVENT)    # not Ravi's event
    with open(store.path, encoding="utf-8") as f:
        assert f.read() == before


def test_decision_reason_and_decider_recorded(store, submit):
    res = submit()
    rules.reject(store, ADMIN, res.id, " Clashes with exams ")
    rules.cancel(store, ADMIN, LAB_EVENT, "  Speaker unavailable ")
    rejected, cancelled = _request(store, res.id), _request(store, LAB_EVENT)
    assert (rejected["decision_reason"], rejected["decided_by"]) == ("Clashes with exams", ADMIN)
    assert (cancelled["decision_reason"], cancelled["decided_by"]) == ("Speaker unavailable", ADMIN)


def test_non_text_title_and_reasons_do_not_crash(store, submit):
    res = submit(title=2026)
    assert res.ok, res.message
    assert _request(store, res.id)["title"] == "2026"
    assert rules.reject(store, ADMIN, res.id, 404).ok
    assert _request(store, res.id)["decision_reason"] == "404"
    assert rules.cancel(store, ADMIN, LAB_EVENT, 7).ok


# ---- staff login

def test_staff_login_with_correct_password(store):
    user = rules.authenticate(store, "Admin ", "admin123")  # username is trimmed, case-insensitive
    assert user["id"] == ADMIN and user["role"] == rules.ADMIN
    assert "password_hash" not in user
    assert rules.authenticate(store, "asha", "asha123")["role"] == rules.REQUESTER


@pytest.mark.parametrize("username,password", [
    ("admin", "wrong"), ("asha", "admin123"), ("nobody", "x"), ("", ""), (None, None),
])
def test_staff_login_refused(store, username, password):
    assert rules.authenticate(store, username, password) is None


def test_passwords_are_not_stored_in_plain_text(store):
    with open(store.path, encoding="utf-8") as f:
        raw = f.read()
    for password in ("admin123", "asha123", "ravi123"):
        assert password not in raw
    assert all("password_hash" not in u for u in rules.list_users(store))


# ---- storage and reads

def test_data_persists_across_store_instances(store, submit, status_of):
    res = submit()
    reopened = Store(store.path)
    assert next(r for r in rules.list_requests(reopened) if r["id"] == res.id)["status"] == rules.PENDING
    with open(store.path, encoding="utf-8") as f:
        assert len(json.load(f)["requests"]) == 3


def test_pending_queue_oldest_first(store, submit):
    a = submit(title="First")
    b = submit(user=RAVI, venue=AMPHI, title="Second")
    assert [r["id"] for r in rules.pending_queue(store)] == [a.id, b.id]


# ---- approve and cancel details

def test_admin_approval_confirms_and_records_decider(store, submit, request_by_id):
    res = submit()
    assert rules.approve(store, ADMIN, res.id).ok
    saved = request_by_id(res.id)
    assert saved["status"] == rules.CONFIRMED
    assert saved["decided_by"] == ADMIN
    assert not rules.approve(store, ADMIN, res.id).ok  # already confirmed


def test_cancel_records_reason(store, request_by_id):
    assert rules.cancel(store, ADMIN, LAB_EVENT, "  Speaker unavailable ").ok
    saved = request_by_id(LAB_EVENT)
    assert saved["status"] == rules.CANCELLED
    assert saved["decision_reason"] == "Speaker unavailable"


def test_actions_on_missing_request_or_user_fail(store):
    assert "does not exist" in rules.approve(store, ADMIN, 999).message
    assert "does not exist" in rules.reject(store, ADMIN, 999, "x").message
    assert rules.cancel(store, UNKNOWN_USER, SEMINAR_EVENT).message == "Unknown user."


def test_list_requests_filters(store, submit):
    submit()
    assert {r["id"] for r in rules.list_requests(store, requester_id=RAVI)} == {LAB_EVENT}
    assert len(rules.list_requests(store, status=rules.CONFIRMED)) == 2
    assert [r["id"] for r in rules.list_requests(store, venue_id=INNOV_LAB)] == [LAB_EVENT]


def test_get_user_hides_password_hash(store):
    user = rules.get_user(store, ASHA)
    assert user["name"] == "Asha" and "password_hash" not in user
    assert rules.get_user(store, UNKNOWN_USER) is None


# ---- reason limits

def test_rejection_reason_is_limited_to_one_short_line(store, submit, status_of):
    res = submit()
    too_long = rules.reject(store, ADMIN, res.id, "x" * (rules.REASON_MAX + 1))
    assert not too_long.ok and "at most 200 characters" in too_long.message
    assert not rules.reject(store, ADMIN, res.id, "Clashes\nwith exams").ok
    assert status_of(res.id) == rules.PENDING
    assert rules.reject(store, ADMIN, res.id, "x" * rules.REASON_MAX).ok


def test_cancellation_reason_is_optional_but_limited(store, status_of):
    assert not rules.cancel(store, ADMIN, LAB_EVENT, "x" * (rules.REASON_MAX + 1)).ok
    assert status_of(LAB_EVENT) == rules.CONFIRMED
    assert rules.cancel(store, ADMIN, LAB_EVENT, "   ").ok  # blank = no reason
    assert _request(store, LAB_EVENT)["decision_reason"] is None
