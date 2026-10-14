"""Fixes from the code review: local-only server, safe demo reset, public schedule,
Markdown escaping."""
from pathlib import Path

import pytest

import rules
from tests.test_flow_e2e import button, open_app
from ui.components import md, md_message

ADMIN, ASHA = 1, 2
AUDITORIUM = 2
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


# ---- public venue schedule

def test_public_schedule_hides_pending_titles(store, submit):
    submit(title="Unannounced Launch")
    public = rules.venue_schedule(store, AUDITORIUM, public=True)
    assert [(row["kind"], row["title"]) for row in public] == [("Pending hold", "Awaiting review")]
    staff = rules.venue_schedule(store, AUDITORIUM)
    assert staff[0]["title"] == "Unannounced Launch"


def _schedule_details(at):
    at.selectbox(key="schedule_venue").set_value(AUDITORIUM).run()
    return at.dataframe[0].value["Details"].tolist()


def test_visitor_sees_held_slot_but_not_title(store, submit):
    submit(title="Unannounced Launch")
    assert _schedule_details(open_app(None, "Venue schedule")) == ["Awaiting review"]
    assert _schedule_details(open_app("ravi", "Venue schedule")) == ["Unannounced Launch"]


# ---- Markdown escaping of user-entered text

LINK_TITLE = "[Approve here](https://evil.example) ![x](https://evil.example/p.png)"


@pytest.mark.parametrize("text", [LINK_TITLE, "**bold** _it_ `code` $x$", "# Heading", "www.evil.example"])
def test_md_leaves_no_live_markdown(text):
    escaped = md(text)
    unescaped_specials = [c for i, c in enumerate(escaped)
                          if c in "[]()!*_`$#:." and (i == 0 or escaped[i - 1] != "\\")]
    assert unescaped_specials == []


def test_md_message_keeps_bullets():
    assert md_message("Cannot approve:\n- Clashes with '[x](y)'.") == \
        "Cannot approve\\:\n- Clashes with '\\[x\\]\\(y\\)'\\."


def test_title_link_is_shown_as_text_to_admin(store, submit):
    assert submit(title=LINK_TITLE).ok
    at = open_app("admin", "Review queue")
    card = next(m.value for m in at.markdown if m.value.startswith("**#3"))
    assert "](" not in card.replace("\\]\\(", "")  # no live link syntax left
    assert "\\[Approve here\\]" in card
