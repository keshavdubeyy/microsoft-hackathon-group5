"""Streamlit entry point for the Campus Event Management System.

Run:  streamlit run app.py

Anyone landing on the portal gets the public attendee view. Staff (Admin,
Requesters) log in from the sidebar. The UI only collects input and shows
results; every decision is made by the rules package.
"""
import streamlit as st

import rules
from ui.admin import page_all_events, page_review_queue, page_venue_blocks
from ui.attendee import page_upcoming_events, page_venue_schedule
from ui.components import flash_and_rerun, get_store, show_flash
from ui.requester import page_my_requests, page_new_request
from ui.theme import apply_theme

st.set_page_config(page_title="Campus Events", layout="wide")
apply_theme()

PUBLIC = "PUBLIC"  # attendees: anyone landing on the portal, no login
PAGES = {
    PUBLIC: ["Upcoming events", "Venue schedule"],
    rules.REQUESTER: ["New request", "My requests", "Venue schedule", "Upcoming events"],
    rules.ADMIN: ["Review queue", "All events", "Venue blocks", "Venue schedule"],
}
PAGE_FUNCS = {
    "New request": page_new_request,
    "My requests": page_my_requests,
    "Review queue": page_review_queue,
    "All events": page_all_events,
    "Venue blocks": page_venue_blocks,
    "Venue schedule": page_venue_schedule,
    "Upcoming events": page_upcoming_events,
}


def login_panel(store):
    """Staff login in the sidebar. The user id is kept in server-side session state."""
    with st.sidebar.form("login", clear_on_submit=True):
        st.markdown("**Staff login**")
        st.caption("For event organisers and admins. Attendees don't need an account.")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.form_submit_button("Log in", type="primary"):
            user = rules.authenticate(store, username, password)
            if user:
                st.session_state["user_id"] = user["id"]
                st.session_state["flash"] = f"Welcome, {user['name']}."
                st.rerun()
            st.error("Invalid username or password.")


def account_panel(store, user):
    st.sidebar.markdown(f"Signed in as **{user['name']}** ({user['role'].title()})")
    if st.sidebar.button("Log out"):
        st.session_state.pop("user_id", None)
        st.rerun()
    if user["role"] == rules.ADMIN:
        reset_controls(store, user)


def reset_controls(store, user):
    """Two-step reset, so one stray click cannot wipe the demo data."""
    if not st.session_state.get("confirm_reset"):
        if st.sidebar.button("Reset demo data"):
            st.session_state["confirm_reset"] = True
            st.rerun()
        return
    st.sidebar.warning("This deletes every request and block added since the start. Reset?")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Yes, reset", type="primary"):
        st.session_state.pop("confirm_reset", None)
        flash_and_rerun(rules.reset_demo_data(store, user["id"]))
    if c2.button("Keep data"):
        st.session_state.pop("confirm_reset", None)
        st.rerun()


def main():
    store = get_store()
    st.sidebar.markdown('<p class="ce-brand">Campus Events</p>', unsafe_allow_html=True)
    # Re-read the user every run, so a removed account is logged out immediately.
    user = rules.get_user(store, st.session_state.get("user_id"))
    role = user["role"] if user else PUBLIC
    page = st.sidebar.radio("Go to", PAGES[role], key=f"page_{role}")

    st.sidebar.divider()
    if user:
        account_panel(store, user)
    else:
        st.session_state.pop("user_id", None)
        login_panel(store)

    show_flash()
    PAGE_FUNCS[page](user)


main()
