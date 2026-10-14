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


def test_t6_end_before_start_is_blocked(submit):
    res = submit(start="2026-08-05 13:00", end="2026-08-05 10:00")
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


def test_unknown_venue_and_bad_datetime_are_blocked(submit):
    assert not submit(venue=99).ok
    assert not submit(start="05/08/2026 10am").ok


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


# ---- Overlap rule (FR-05, A1): new_start < existing_end AND new_end > existing_start

@pytest.mark.parametrize("start,end,expected", [
    ("10:00", "12:00", True),   # exact same slot
    ("10:30", "11:30", True),   # inside the existing booking
    ("09:00", "13:00", True),   # contains the existing booking
    ("09:00", "10:30", True),   # partial overlap on the left
    ("11:30", "13:00", True),   # partial overlap on the right
    ("08:00", "10:00", False),  # back-to-back before
    ("12:00", "14:00", False),  # back-to-back after
    ("13:00", "14:00", False),  # clearly apart
])
def test_overlap_rule(start, end, expected):
    day = "2026-08-04 "
    assert rules.overlaps(day + start, day + end, day + "10:00", day + "12:00") is expected


def test_same_time_at_another_venue_is_allowed(submit):
    res = submit(venue=2, start="2026-08-04 10:00", end="2026-08-04 12:00")  # Main Auditorium
    assert res.ok, res.message


def test_request_right_after_block_is_allowed(submit):
    res = submit(venue=CONF_C, start="2026-08-04 18:00", end="2026-08-04 19:00", attendance=20)
    assert res.ok, res.message


def test_multi_day_request_spanning_a_block_is_blocked(submit):
    res = submit(venue=CONF_C, start="2026-08-03 12:00", end="2026-08-05 12:00", attendance=20)
    assert not res.ok
    assert "Conference Room C is unavailable (Renovation)" in res.message


def test_attendance_equal_to_capacity_is_allowed(submit):
    res = submit(venue=INNOV_LAB, start="2026-08-07 10:00", end="2026-08-07 12:00", attendance=60)
    assert res.ok, res.message


def test_zero_length_event_is_blocked(submit):
    res = submit(start="2026-08-05 10:00", end="2026-08-05 10:00")
    assert not res.ok
    assert "End date-time must be after start" in res.message


def test_every_conflict_is_listed(store, submit):
    assert submit(venue=SEMINAR_A, start="2026-08-04 12:00", end="2026-08-04 14:00").ok
    reasons = rules.validate_request(store, "Day-long fest", "Cultural Programme", SEMINAR_A,
                                     "2026-08-04 09:00", "2026-08-04 18:00", 100)
    assert len(reasons) == 2
    assert any("confirmed event 'AI Workshop'" in r for r in reasons)
    assert any("pending request 'Test Event'" in r for r in reasons)


def test_unknown_event_type_is_blocked(submit):
    res = submit(event_type="Wedding")
    assert not res.ok
    assert "Event type must be one of" in res.message
