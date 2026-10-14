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


def test_block_on_unknown_venue_or_bad_window_is_refused(store):
    assert "does not exist" in rules.add_block(store, ADMIN, 99, "2026-08-08 10:00", "2026-08-08 12:00", "x").message
    assert not rules.add_block(store, ADMIN, AMPHI, "2026-08-08 12:00", "2026-08-08 10:00", "x").ok
    assert not rules.add_block(store, ADMIN, AMPHI, "tomorrow", "2026-08-08 10:00", "x").ok


def test_removing_missing_block_fails(store):
    assert "does not exist" in rules.remove_block(store, ADMIN, 999).message


def test_list_blocks_includes_venue_name(store):
    blocks = rules.list_blocks(store)
    assert [(b["venue_name"], b["reason"]) for b in blocks] == [("Conference Room C", "Renovation")]
    assert rules.list_blocks(store, venue_id=AMPHI) == []
