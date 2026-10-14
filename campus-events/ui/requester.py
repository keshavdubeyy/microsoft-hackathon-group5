"""Requester pages: new request (with live checks) and my requests."""
import streamlit as st

import rules
from ui.components import (
    STATUSES, cancel_controls, datetime_inputs, flash_and_rerun, get_store, render_schedule,
    request_card, search_box, venue_picker,
)


def page_new_request(user):
    st.header("New event request")


def page_my_requests(user):
    st.header("My requests")
