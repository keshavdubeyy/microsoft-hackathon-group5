"""Pure helpers in rules.models and rules.validation (no data file needed)."""
from datetime import datetime

import pytest

import rules


@pytest.mark.parametrize("a,b,expected", [
    (("10:00", "12:00"), ("11:00", "13:00"), True),   # partial overlap
    (("10:00", "12:00"), ("10:30", "11:30"), True),   # contained
    (("10:00", "12:00"), ("09:00", "13:00"), True),   # contains
    (("10:00", "12:00"), ("12:00", "14:00"), False),  # back-to-back
    (("10:00", "12:00"), ("08:00", "10:00"), False),  # back-to-back, before
    (("10:00", "12:00"), ("13:00", "14:00"), False),  # apart
])
def test_overlaps(a, b, expected):
    day = "2026-08-04 "
    assert rules.overlaps(day + a[0], day + a[1], day + b[0], day + b[1]) is expected
    assert rules.overlaps(day + b[0], day + b[1], day + a[0], day + a[1]) is expected  # symmetric


def test_to_dt_str_accepts_datetime_and_trimmed_string():
    assert rules.to_dt_str(datetime(2026, 8, 4, 9, 5)) == "2026-08-04 09:05"
    assert rules.to_dt_str("  2026-08-04 09:05 ") == "2026-08-04 09:05"


@pytest.mark.parametrize("value", ["2026-08-04", "04/08/2026 10:00", "2026-13-01 10:00", "", None])
def test_to_dt_str_rejects_bad_values(value):
    with pytest.raises(ValueError):
        rules.to_dt_str(value)


def test_describe_window_same_day():
    assert rules.describe_window("2026-08-04 10:00", "2026-08-04 12:00") == "4 Aug 2026, 10:00–12:00"


def test_describe_window_multi_day():
    assert (rules.describe_window("2026-08-10 09:00", "2026-08-11 18:00")
            == "10 Aug 2026 09:00 – 11 Aug 2026 18:00")


def test_only_pending_and_confirmed_hold_a_slot():
    assert set(rules.ACTIVE) == {rules.PENDING, rules.CONFIRMED}
    assert rules.REJECTED not in rules.ACTIVE and rules.CANCELLED not in rules.ACTIVE
