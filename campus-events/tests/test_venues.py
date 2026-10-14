"""Venue blocks (T10) and venue schedules."""
import rules

ADMIN, ASHA = 1, 2
SEMINAR_A, CONF_C, AMPHI = 1, 3, 4


def test_t10_block_over_confirmed_event_is_refused(store):
    res = rules.add_block(store, ADMIN, SEMINAR_A, "2026-08-04 08:00", "2026-08-04 11:00", "Maintenance")
    assert not res.ok
    assert "AI Workshop" in res.message


def test_block_prevents_new_requests_and_removal_frees(store, submit):
    block = rules.add_block(store, ADMIN, AMPHI, "2026-08-08 00:00", "2026-08-09 00:00", "Maintenance")
    assert block.ok, block.message
    assert not submit(venue=AMPHI, start="2026-08-08 10:00", end="2026-08-08 12:00").ok

    assert rules.remove_block(store, ADMIN, block.id).ok
    assert submit(venue=AMPHI, start="2026-08-08 10:00", end="2026-08-08 12:00").ok


def test_only_admin_manages_blocks(store):
    assert not rules.add_block(store, ASHA, AMPHI, "2026-08-08 10:00", "2026-08-08 12:00", "x").ok
    assert not rules.remove_block(store, ASHA, 1).ok


def test_block_requires_reason(store):
    assert not rules.add_block(store, ADMIN, AMPHI, "2026-08-08 10:00", "2026-08-08 12:00", "").ok


def test_venue_schedule_shows_events_holds_and_blocks(store, submit):
    submit(venue=CONF_C, start="2026-08-05 10:00", end="2026-08-05 11:00", attendance=10)
    kinds = [row["kind"] for row in rules.venue_schedule(store, CONF_C)]
    assert kinds == ["Blocked", "Pending hold"]
    assert [row["kind"] for row in rules.venue_schedule(store, SEMINAR_A)] == ["Event"]


# ---- A7: a block never silently overrides a booking

def test_block_over_pending_request_is_refused(store, submit):
    assert submit(venue=AMPHI, start="2026-08-08 10:00", end="2026-08-08 12:00").ok
    res = rules.add_block(store, ADMIN, AMPHI, "2026-08-08 09:00", "2026-08-08 18:00", "Maintenance")
    assert not res.ok
    assert "pending request 'Test Event'" in res.message


def test_block_right_after_event_is_allowed(store):
    res = rules.add_block(store, ADMIN, SEMINAR_A, "2026-08-04 12:00", "2026-08-04 18:00", "Maintenance")
    assert res.ok, res.message


def test_block_over_cancelled_event_is_allowed(store):
    assert rules.cancel(store, ADMIN, 1).ok  # seeded AI Workshop at Seminar Hall A
    res = rules.add_block(store, ADMIN, SEMINAR_A, "2026-08-04 09:00", "2026-08-04 18:00", "Maintenance")
    assert res.ok, res.message


def test_block_over_rejected_request_is_allowed(store, submit):
    pending = submit(venue=AMPHI, start="2026-08-08 10:00", end="2026-08-08 12:00")
    assert rules.reject(store, ADMIN, pending.id, "Exams").ok
    res = rules.add_block(store, ADMIN, AMPHI, "2026-08-08 09:00", "2026-08-08 18:00", "Maintenance")
    assert res.ok, res.message


# ---- block validation

def test_block_with_invalid_times_is_refused(store):
    assert "End date-time must be after start" in rules.add_block(
        store, ADMIN, AMPHI, "2026-08-08 18:00", "2026-08-08 09:00", "Maintenance").message
    assert "valid date-times" in rules.add_block(
        store, ADMIN, AMPHI, "08/08/2026", "2026-08-08 09:00", "Maintenance").message


def test_block_on_unknown_venue_is_refused(store):
    res = rules.add_block(store, ADMIN, 99, "2026-08-08 09:00", "2026-08-08 18:00", "Maintenance")
    assert not res.ok
    assert "venue does not exist" in res.message


def test_block_only_affects_its_own_venue(store, submit):
    assert rules.add_block(store, ADMIN, AMPHI, "2026-08-08 09:00", "2026-08-08 18:00", "Maintenance").ok
    assert submit(venue=2, start="2026-08-08 10:00", end="2026-08-08 12:00").ok  # Main Auditorium


def test_refused_block_does_not_touch_file(store):
    with open(store.path, encoding="utf-8") as f:
        before = f.read()
    rules.add_block(store, ADMIN, SEMINAR_A, "2026-08-04 09:00", "2026-08-04 18:00", "Maintenance")
    with open(store.path, encoding="utf-8") as f:
        assert f.read() == before


def test_remove_unknown_block_is_refused(store):
    res = rules.remove_block(store, ADMIN, 99)
    assert not res.ok
    assert "does not exist" in res.message


def test_block_reports_all_reasons_together(store):
    res = rules.add_block(store, ADMIN, SEMINAR_A, "2026-08-04 08:00", "2026-08-04 11:00", "  ")
    assert not res.ok
    assert "reason is required" in res.message
    assert "AI Workshop" in res.message
