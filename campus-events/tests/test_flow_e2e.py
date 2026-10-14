"""End-to-end flows: T1 through the rules, then the real Streamlit app driven
headlessly with AppTest (login, forms, buttons, on-screen messages)."""
from datetime import date, time
from pathlib import Path

from streamlit.testing.v1 import AppTest

import rules

APP = str(Path(__file__).resolve().parent.parent / "app.py")
CREDENTIALS = {"admin": "admin123", "asha": "asha123", "ravi": "ravi123"}
SEMINAR_A, AUDITORIUM = 1, 2



def test_t1_submit_approve_cancel_releases_slot(store, submit, status_of):
    res = submit(attendance=300)
    assert res.ok, res.message
    assert status_of(res.id) == rules.PENDING

    assert rules.approve(store, 1, res.id).ok
    assert status_of(res.id) == rules.CONFIRMED

    assert rules.cancel(store, 2, res.id).ok
    assert status_of(res.id) == rules.CANCELLED

    again = submit(user=3, attendance=300)
    assert again.ok, again.message


# ---- UI flows


def login(at, username, password):
    at.sidebar.text_input(key="login_username").input(username)
    at.sidebar.text_input(key="login_password").input(password)
    button(at, "Log in").click().run()
    return at


def open_app(username, page):
    """Open the portal, log in (None = public attendee view) and go to a page."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    role = "PUBLIC"
    if username:
        login(at, username, CREDENTIALS[username])
        role = "ADMIN" if username == "admin" else "REQUESTER"
    at.sidebar.radio(key=f"page_{role}").set_value(page).run()
    assert not at.exception, at.exception
    return at


def button(at, label):
    return next(b for b in at.button if b.label == label)


def fill_request(at, title, venue, day, start, end, attendance):
    at.text_input(key="title_0").input(title)
    at.selectbox(key="venue_0").set_value(venue)
    at.number_input(key="att_0").set_value(attendance)
    at.date_input(key="req_0_sd").set_value(day)
    at.date_input(key="req_0_ed").set_value(day)
    at.time_input(key="req_0_st").set_value(start)
    at.time_input(key="req_0_et").set_value(end)
    return at.run()


def test_end_to_end_submit_approve_cancel(store, status_of):
    # Requester submits
    at = open_app("asha", "New request")
    fill_request(at, "Freshers Hackathon", AUDITORIUM, date(2026, 8, 5), time(10, 0), time(13, 0), 300)
    assert "available" in at.info[0].value
    button(at, "Submit request").click().run()
    assert "submitted" in at.success[0].value
    assert status_of(3) == rules.PENDING

    # Admin approves from the queue
    at = open_app("admin", "Review queue")
    assert any("Freshers Hackathon" in m.value for m in at.markdown)
    at.button(key="approve_3").click().run()
    assert "confirmed" in at.success[0].value
    assert status_of(3) == rules.CONFIRMED

    # Attendee sees it
    at = open_app(None, "Upcoming events")
    assert "Freshers Hackathon" in at.dataframe[0].value["Event"].tolist()

    # Requester cancels; slot is free again
    at = open_app("asha", "My requests")
    at.button(key="cancel_3").click().run()
    assert "cancelled" in at.success[0].value
    assert status_of(3) == rules.CANCELLED


def test_conflict_is_shown_and_submit_disabled(store):
    at = open_app("ravi", "New request")
    fill_request(at, "Clashing Talk", SEMINAR_A, date(2026, 8, 4), time(11, 0), time(13, 0), 50)
    assert "AI Workshop" in at.warning[0].value
    assert button(at, "Submit request").disabled
    assert len(rules.list_requests(store)) == 2


def test_capacity_shown_before_submit(store):
    at = open_app("ravi", "New request")
    fill_request(at, "Big Lab Session", 5, date(2026, 8, 7), time(10, 0), time(12, 0), 200)
    assert "capacity of 60" in at.warning[0].value
    assert button(at, "Submit request").disabled


def test_reject_needs_reason_then_works(store, status_of):
    rules.submit_request(store, 3, "Club Meetup", "Club Activity", AUDITORIUM,
                         "2026-08-05 15:00", "2026-08-05 16:00", 40)
    at = open_app("admin", "Review queue")
    assert at.button(key="reject_3").disabled  # cannot reject without a reason
    assert status_of(3) == rules.PENDING

    at.text_input(key="reject_reason_3").input("   ").run()
    assert at.button(key="reject_3").disabled  # blanks do not count

    at.text_input(key="reject_reason_3").input("Auditorium reserved for exams").run()
    assert not at.button(key="reject_3").disabled
    at.button(key="reject_3").click().run()
    assert "rejected" in at.success[0].value
    assert status_of(3) == rules.REJECTED


def test_admin_block_over_event_is_refused(store):
    at = open_app("admin", "Venue blocks")
    at.selectbox(key="block_venue").set_value(SEMINAR_A)
    at.date_input(key="block_sd").set_value(date(2026, 8, 4))
    at.date_input(key="block_ed").set_value(date(2026, 8, 4))
    at.run()
    button(at, "Add block").click().run()
    assert "AI Workshop" in at.error[0].value
    assert len(rules.list_blocks(store)) == 1


def test_landing_page_is_public_attendee_view(store):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert at.sidebar.radio(key="page_PUBLIC").options == ["Upcoming events", "Venue schedule"]
    assert at.header[0].value == "Confirmed events"
    assert "AI Workshop" in at.dataframe[0].value["Event"].tolist()
    assert not [b for b in at.button if b.label in ("Approve", "Reject", "Cancel event", "Reset demo data")]


def test_wrong_password_stays_public(store):
    at = AppTest.from_file(APP, default_timeout=30).run()
    login(at, "admin", "not-the-password")
    assert "Invalid username or password" in at.sidebar.error[0].value
    assert at.sidebar.radio(key="page_PUBLIC")
    assert "user_id" not in at.session_state


def test_requester_login_sees_requester_pages_only(store):
    at = open_app("asha", "My requests")
    assert "Review queue" not in at.sidebar.radio(key="page_REQUESTER").options
    assert any("Signed in as **Asha**" in m.value for m in at.sidebar.markdown)
    assert not [b for b in at.button if b.label == "Reset demo data"]


def test_logout_returns_to_public_view(store):
    at = open_app("admin", "Review queue")
    button(at, "Log out").click().run()
    assert at.sidebar.radio(key="page_PUBLIC")
    assert "user_id" not in at.session_state
