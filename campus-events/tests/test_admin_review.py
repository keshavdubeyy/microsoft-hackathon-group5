"""Admin review queue details and the searchable All events page."""
import pytest

import rules
from db.seed import demo_requests
from tests.test_flow_e2e import button, open_app


@pytest.fixture
def demo(store):
    with store.transaction() as data:
        data["requests"].extend(demo_requests())
    return store


def test_search_matches_title_venue_requester_and_id(demo):
    assert [r["id"] for r in rules.search_requests(demo, "hackathon")] == [3]
    assert {r["id"] for r in rules.search_requests(demo, "innovation lab")} == {2, 5}
    assert {r["id"] for r in rules.search_requests(demo, "ravi")} == {2, 4, 6, 8}
    assert [r["id"] for r in rules.search_requests(demo, "9")] == [9]
    assert rules.search_requests(demo, "no such event") == []


def test_search_filters_by_multiple_statuses(demo):
    rows = rules.search_requests(demo, "", [rules.REJECTED, rules.CANCELLED])
    assert {r["id"] for r in rows} == {8, 9}
    assert len(rules.search_requests(demo, "", [])) == 9  # empty = no status filter


def test_review_details_for_pending_request(demo):
    d = rules.review_details(demo, 4)  # 110 people, Seminar Hall A (capacity 120), 2 hours
    assert d["capacity"] == 120 and d["fill_percent"] == 92
    assert d["duration_hours"] == 2.0
    assert d["conflicts"] == []  # back-to-back with AI Workshop is allowed
    assert [row["title"] for row in d["same_day_schedule"]] == ["AI Workshop"]
    assert rules.review_details(demo, 999) is None


def test_review_details_reports_requester_history(demo):
    d = rules.review_details(demo, 6)  # Ravi: one confirmed (#2), one rejected (#8)
    assert d["requester_confirmed"] == 1 and d["requester_rejected"] == 1


def test_queue_shows_details_and_approves(demo, status_of):
    at = open_app("admin", "Review queue")
    assert len(at.metric) == 4 * 4  # four pending requests, four figures each
    assert any("No clashes" in i.value for i in at.info)
    at.button(key="approve_4").click().run()
    assert status_of(4) == rules.CONFIRMED


def test_all_events_search_and_status_filter(demo):
    at = open_app("admin", "All events")
    assert len(at.dataframe[0].value) == 9
    at.text_input(key="all_search").input("ravi").run()
    assert set(at.dataframe[0].value["#"]) == {2, 4, 6, 8}
    at.multiselect(key="all_status").set_value([rules.REJECTED]).run()
    assert at.dataframe[0].value["Event"].tolist() == ["Open Mic Evening"]


def test_all_events_cancel_from_expander(demo, status_of):
    at = open_app("admin", "All events")
    at.selectbox(key="cancel_event").set_value(7).run()
    button(at, "Cancel event").click().run()
    assert status_of(7) == rules.CANCELLED


def test_confirmed_events_page_is_searchable(demo):
    at = open_app(None, "Upcoming events")
    assert len(at.dataframe[0].value) == 3  # AI Workshop, Python Coding Bootcamp, Inter-College Quiz
    at.text_input(key="events_search").input("quiz").run()
    assert at.dataframe[0].value["Event"].tolist() == ["Inter-College Quiz"]
    at.text_input(key="events_search").input("zzz").run()
    assert not at.dataframe and "match your search" in at.info[0].value


def test_my_requests_search_only_covers_own_requests(demo):
    at = open_app("asha", "My requests")
    all_titles = [m.value for m in at.markdown if m.value.startswith("**#")]
    assert len(all_titles) == 5  # Asha owns #1, #3, #5, #7, #9
    at.text_input(key="my_search").input("robotics").run()
    assert [m.value for m in at.markdown if m.value.startswith("**#")] == ["**#5 Robotics Club Demo** · Club Activity"]
    at.text_input(key="my_search").input("ravi").run()  # Ravi's requests are not Asha's
    assert "match the search" in at.info[0].value
