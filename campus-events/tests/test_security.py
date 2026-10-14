"""Fixes from the code review: local-only server, safe demo reset."""
from pathlib import Path

import pytest

import rules
from tests.test_flow_e2e import button, open_app

ADMIN, ASHA = 1, 2
CONFIG = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"


# ---- server is local only

def test_server_listens_on_localhost_only():
    tomllib = pytest.importorskip("tomllib")  # Python 3.11+
    with open(CONFIG, "rb") as f:
        assert tomllib.load(f)["server"]["address"] == "localhost"


# ---- demo reset

def test_reset_restores_seed_data_for_admin_only(store, submit):
    submit()
    assert not rules.reset_demo_data(store, ASHA).ok
    assert len(rules.list_requests(store)) == 3

    assert rules.reset_demo_data(store, ADMIN).ok
    assert [r["id"] for r in rules.list_requests(store)] == [1, 2]
    assert rules.authenticate(store, "admin", "admin123")  # accounts still work


def test_reset_needs_confirmation_in_ui(store, submit):
    submit()
    at = open_app("admin", "Review queue")
    button(at, "Reset demo data").click().run()
    assert len(rules.list_requests(store)) == 3  # first click only asks

    button(at, "Keep data").click().run()
    assert len(rules.list_requests(store)) == 3

    button(at, "Reset demo data").click().run()
    button(at, "Yes, reset").click().run()
    assert "reset" in at.success[0].value
    assert len(rules.list_requests(store)) == 2
