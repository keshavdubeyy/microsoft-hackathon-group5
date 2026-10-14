"""Shared fixtures: a fresh, seeded data file per test.

Seed ids: users 1 Admin, 2 Asha, 3 Ravi (passwords admin123/asha123/ravi123);
venues 1 Seminar Hall A, 2 Main Auditorium, 3 Conference Room C,
4 Central Amphitheatre, 5 Innovation Lab; requests 1 (Asha, Seminar Hall A,
4 Aug 10-12) and 2 (Ravi, Innovation Lab, 6 Aug 14-17) are CONFIRMED;
block 1 is Conference Room C renovation on 4 Aug 09-18.
"""
import pytest

import rules
from db import Store


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = str(tmp_path / "events.json")
    monkeypatch.setenv("EVENTS_DB", path)  # the Streamlit app under test uses the same file
    return Store(path)


@pytest.fixture
def submit(store):
    """Submit a request with sensible defaults (Asha, Main Auditorium, 5 Aug 10-13)."""
    def _submit(user=2, venue=2, start="2026-08-05 10:00", end="2026-08-05 13:00",
                attendance=100, title="Test Event", event_type="Hackathon"):
        return rules.submit_request(store, user, title, event_type, venue, start, end, attendance)
    return _submit


@pytest.fixture
def request_by_id(store):
    """Look up a full request record by id; fails the test clearly if it is missing."""
    def _request_by_id(request_id):
        match = next((r for r in rules.list_requests(store) if r["id"] == request_id), None)
        assert match is not None, f"request {request_id} not found"
        return match
    return _request_by_id


@pytest.fixture
def status_of(request_by_id):
    def _status_of(request_id):
        return request_by_id(request_id)["status"]
    return _status_of
