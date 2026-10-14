"""Requester pages: new request (with live checks) and my requests."""
import streamlit as st

import rules
from ui.components import (
    STATUSES, cancel_controls, datetime_inputs, flash_and_rerun, get_store, render_schedule,
    request_card, search_box, venue_picker,
)


def page_new_request(user):
    store = get_store()
    st.header("New event request")
    st.caption("Checks run as you type; a request that would fail cannot be submitted.")
    # Bumping the version gives the widgets fresh keys, clearing the form after a submit.
    v = st.session_state.setdefault("form_version", 0)
    title = st.text_input("Event title", key=f"title_{v}")
    c1, c2, c3 = st.columns([2, 3, 1])
    event_type = c1.selectbox("Event type", rules.EVENT_TYPES, key=f"type_{v}")
    venue = venue_picker(c2, f"venue_{v}")
    attendance = int(c3.number_input("Expected attendance", min_value=1, value=50, step=1, key=f"att_{v}"))
    start, end = datetime_inputs(f"req_{v}")

    reasons = rules.validate_request(store, title, event_type, venue["id"], start, end, attendance)
    if reasons:
        st.warning("Fix before submitting:\n" + "\n".join(f"- {r}" for r in reasons))
    else:
        st.info(f"{venue['name']} is available for "
                f"{rules.describe_window(rules.to_dt_str(start), rules.to_dt_str(end))}.")

    if st.button("Submit request", type="primary", disabled=bool(reasons)):
        # submit_request re-validates against the saved data, so a slot taken
        # by someone else since the check above is still refused.
        result = rules.submit_request(store, user["id"], title, event_type, venue["id"], start, end, attendance)
        if result.ok:
            st.session_state["form_version"] = v + 1
        flash_and_rerun(result)

    with st.expander(f"Current schedule for {venue['name']}"):
        render_schedule(venue["id"])


def page_my_requests(user):
    st.header("My requests")
    store = get_store()
    requests = rules.list_requests(store, requester_id=user["id"])
    if not requests:
        st.info("You have not submitted any requests yet. Use **New request** in the sidebar to book a venue.")
        return

    # Status summary, so the requester sees at a glance what needs attention.
    for col, status in zip(st.columns(len(STATUSES)), STATUSES):
        col.metric(status.title(), sum(r["status"] == status for r in requests))

    c1, c2 = st.columns([3, 1])
    with c1:
        text = search_box("my_search")
    status = c2.selectbox("Show", ["All"] + STATUSES, format_func=str.title, key="my_requests_status")
    shown = rules.search_requests(
        store, text, None if status == "All" else [status], requester_id=user["id"], recent_first=True
    )
    if not shown:
        st.info("None of your requests match the search and status filter.")
    for r in shown:
        box = request_card(r)
        if r["status"] == rules.CONFIRMED:
            cancel_controls(box, user, r)
