"""Public pages (no login): confirmed events and venue schedules. Also used by staff."""
import streamlit as st

import rules
from ui.components import get_store, render_schedule, search_box, venue_picker, window


def page_upcoming_events(user):
    st.header("Confirmed events")
    text = search_box("events_search")
    events = rules.search_requests(get_store(), text, [rules.CONFIRMED])
    if not events:
        st.info("No confirmed events match your search." if text.strip() else "No confirmed events yet.")
        return
    venue_names = sorted({e["venue_name"] for e in events})
    chosen = st.selectbox("Filter by venue", ["All venues"] + venue_names, key="events_venue_filter")
    if chosen != "All venues":
        events = [e for e in events if e["venue_name"] == chosen]
    st.caption(f"{len(events)} confirmed event(s), earliest first.")
    st.dataframe(
        [{"Event": e["title"], "Type": e["event_type"], "Venue": e["venue_name"], "When": window(e)}
         for e in events],
        hide_index=True, width="stretch",
    )


def page_venue_schedule(user):
    st.header("Venue schedule")
    venue = venue_picker(st, "schedule_venue")
    render_schedule(venue["id"])
