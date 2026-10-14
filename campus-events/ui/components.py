"""Shared widgets and helpers used by the role pages."""
import re
from datetime import date, datetime, time

import streamlit as st

import rules
from db import Store
from ui.theme import chip

STATUSES = [rules.PENDING, rules.CONFIRMED, rules.REJECTED, rules.CANCELLED]
DEFAULT_DATE = date(2026, 8, 5)  # near the brief's seed data, so demos start in the right week

# Markdown punctuation, plus ':' and '.' so typed URLs don't become autolinks.
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#+!|~$:.])")


def md(text):
    """Escape user-entered text for st.markdown, so a title can't render as a link or image."""
    return _MD_SPECIAL.sub(r"\\\1", str(text))


def md_message(message):
    """Escape a rules message, keeping its '- ' lines as a bullet list."""
    return "\n".join(
        "- " + md(line[2:]) if line.startswith("- ") else md(line)
        for line in str(message).split("\n")
    )


def get_store():
    """A Store for this run. Cheap to create; all Stores share one lock per file."""
    return Store()


def flash_and_rerun(result):
    """Show a success after the rerun (so lists refresh); show failures in place."""
    if result.ok:
        st.session_state["flash"] = result.message
        st.rerun()
    else:
        st.error(md_message(result.message))


def show_flash():
    message = st.session_state.pop("flash", None)
    if message:
        st.success(md_message(message))


def venue_picker(container, key):
    """Venue selectbox (options are ids, so selection survives reruns). Returns the venue dict."""
    venues = {v["id"]: v for v in rules.list_venues(get_store())}
    venue_id = container.selectbox(
        "Venue", list(venues), key=key,
        format_func=lambda i: f"{venues[i]['name']} — {venues[i]['type']}, capacity {venues[i]['capacity']}",
    )
    return venues[venue_id]


def datetime_inputs(prefix, start_time=time(10, 0), end_time=time(12, 0)):
    """Start and end date + time pickers. Returns (start, end) datetimes."""
    c1, c2, c3, c4 = st.columns(4)
    start_d = c1.date_input("Start date", DEFAULT_DATE, key=f"{prefix}_sd")
    start_t = c2.time_input("Start time", start_time, key=f"{prefix}_st")
    end_d = c3.date_input("End date", DEFAULT_DATE, key=f"{prefix}_ed")
    end_t = c4.time_input("End time", end_time, key=f"{prefix}_et")
    return datetime.combine(start_d, start_t), datetime.combine(end_d, end_t)


def window(row):
    return rules.describe_window(row["start"], row["end"])


def request_card(r, show_requester=False):
    """Bordered summary of one request; returns the container for action buttons."""
    box = st.container(border=True)
    left, right = box.columns([4, 1])
    left.markdown(f"**#{r['id']} {md(r['title'])}** · {r['event_type']}")
    who = f" · requested by {r['requester_name']}" if show_requester else ""
    left.caption(f"{r['venue_name']} · {window(r)} · {r['attendance']} attendees{who}")
    right.markdown(chip(r["status"].title(), r["status"].lower()), unsafe_allow_html=True)
    if r["decision_reason"]:
        box.caption(f"Reason: {md(r['decision_reason'])}")
    return box


def cancel_controls(box, user, r):
    c1, c2 = box.columns([4, 1])
    reason = c1.text_input("Cancellation reason (optional)", key=f"cancel_reason_{r['id']}",
                           label_visibility="collapsed", placeholder="Cancellation reason (optional)",
                           max_chars=rules.REASON_MAX)
    if c2.button("Cancel event", key=f"cancel_{r['id']}"):
        flash_and_rerun(rules.cancel(get_store(), user["id"], r["id"], reason))


def render_schedule(venue_id, public=False):
    rows = rules.venue_schedule(get_store(), venue_id, public=public)
    if not rows:
        st.info("Nothing booked or blocked — the venue is free.")
        return
    st.dataframe(
        [{"Type": row["kind"], "When": window(row), "Details": row["title"]} for row in rows],
        hide_index=True, width="stretch",
    )
