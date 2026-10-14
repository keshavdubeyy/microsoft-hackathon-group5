"""Validation before submission (T2-T6): refused requests are never saved."""
import pytest

import rules

ASHA, RAVI = 2, 3
SEMINAR_A, CONF_C, INNOV_LAB = 1, 3, 5


def test_t2_overlap_with_confirmed_event_is_blocked(store, submit):
    res = submit(venue=SEMINAR_A, start="2026-08-04 11:00", end="2026-08-04 13:00")
    assert not res.ok
    assert "AI Workshop" in res.message and "10:00–12:00" in res.message
    assert len(rules.list_requests(store)) == 2  # nothing saved


def test_t3_back_to_back_is_allowed(submit):
    res = submit(venue=SEMINAR_A, start="2026-08-04 12:00", end="2026-08-04 14:00")
    assert res.ok, res.message


def test_t4_renovation_block_is_blocked(submit):
    res = submit(venue=CONF_C, start="2026-08-04 14:00", end="2026-08-04 15:00", attendance=20)
    assert not res.ok
    assert "Renovation" in res.message


def test_t5_capacity_exceeded_is_blocked(submit):
    res = submit(venue=INNOV_LAB, start="2026-08-07 10:00", end="2026-08-07 12:00", attendance=200)
    assert not res.ok
    assert "capacity of 60" in res.message


@pytest.mark.parametrize("start,end", [
    ("2026-08-05 13:00", "2026-08-05 10:00"),  # T6: end before start
    ("2026-08-05 10:00", "2026-08-05 10:00"),  # zero-length event
])
def test_t6_end_not_after_start_is_blocked(submit, start, end):
    res = submit(start=start, end=end)
    assert not res.ok
    assert "End date-time must be after start" in res.message


def test_all_reasons_reported_together(submit):
    res = submit(venue=CONF_C, start="2026-08-04 10:00", end="2026-08-04 11:00",
                 attendance=80, title="  ")
    assert not res.ok
    for text in ("title is required", "capacity of 40", "Renovation"):
        assert text in res.message


@pytest.mark.parametrize("attendance", [0, -5, 2.5, "10", True])
def test_invalid_attendance_is_blocked(submit, attendance):
    assert not submit(attendance=attendance).ok


@pytest.mark.parametrize("overrides,expected", [
    ({"venue": 99}, "venue does not exist"),
    ({"start": "05/08/2026 10am"}, "valid date-times"),
    ({"end": ""}, "valid date-times"),
    ({"event_type": "Party"}, "Event type must be one of"),
    ({"title": None}, "title is required"),
])
def test_bad_input_is_blocked_with_reason(submit, overrides, expected):
    res = submit(**overrides)
    assert not res.ok
    assert expected in res.message


def test_multi_day_event_is_allowed(submit):
    res = submit(venue=INNOV_LAB, start="2026-08-10 09:00", end="2026-08-11 18:00", attendance=60)
    assert res.ok, res.message
    clash = submit(user=RAVI, venue=INNOV_LAB, start="2026-08-11 08:00",
                   end="2026-08-11 09:00", attendance=10)
    assert not clash.ok


def test_failed_submit_does_not_touch_file(store, submit):
    with open(store.path, encoding="utf-8") as f:
        before = f.read()
    submit(venue=CONF_C, start="2026-08-04 10:00", end="2026-08-04 11:00", attendance=10)
    with open(store.path, encoding="utf-8") as f:
        assert f.read() == before


def test_live_check_matches_submit(store):
    reasons = rules.validate_request(store, "Talk", "Hackathon", SEMINAR_A,
                                     "2026-08-04 11:00", "2026-08-04 13:00", 50)
    assert len(reasons) == 1 and "AI Workshop" in reasons[0]


def test_successful_submit_is_saved_as_pending(submit, request_by_id):
    res = submit(title="  Spaced Title  ")
    assert res.ok, res.message
    saved = request_by_id(res.id)
    assert saved["status"] == rules.PENDING
    assert saved["title"] == "Spaced Title"  # surrounding whitespace is trimmed
    assert saved["venue_name"] == "Main Auditorium"
    assert saved["requester_name"] == "Asha"


def test_attendance_equal_to_capacity_is_allowed(submit):
    res = submit(venue=INNOV_LAB, start="2026-08-07 10:00", end="2026-08-07 12:00", attendance=60)
    assert res.ok, res.message
