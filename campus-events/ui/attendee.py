"""Public pages (no login): confirmed events and venue schedules. Also used by staff."""
import streamlit as st

import rules
from ui.components import get_store, render_schedule, search_box, venue_picker, window


def page_upcoming_events(user):
    st.header("Confirmed events")


def page_venue_schedule(user):
    st.header("Venue schedule")
    venue = venue_picker(st, "schedule_venue")
    render_schedule(venue["id"])
