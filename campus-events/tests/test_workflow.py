"""Lifecycle, roles and login (T7-T9)."""
import json

import pytest

import rules
from db import Store

ADMIN, ASHA, RAVI, UNKNOWN_USER = 1, 2, 3, 99
AMPHI, INNOV_LAB = 4, 5
SEMINAR_EVENT, LAB_EVENT = 1, 2  # seeded confirmed events (Asha, Ravi)


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
