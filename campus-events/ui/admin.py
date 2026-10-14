"""Admin pages: review queue, all events, venue blocks."""
from datetime import time

import streamlit as st

import rules
from ui.components import (
    STATUSES, cancel_controls, datetime_inputs, flash_and_rerun, get_store, request_card,
    venue_picker, window,
)

BLOCK_REASONS = ["Maintenance", "Renovation", "Other operational restriction"]


def page_review_queue(user):
    store = get_store()
    st.header("Review queue")
    queue = rules.pending_queue(store)
    st.caption(f"{len(queue)} pending request(s), oldest first. Pending requests hold their venue slot.")
    for r in queue:
        box = request_card(r, show_requester=True)
        c1, c2, c3 = box.columns([1, 3, 1])
        if c1.button("Approve", key=f"approve_{r['id']}"):
            flash_and_rerun(rules.approve(store, user["id"], r["id"]))
        reason = c2.text_input("Rejection reason", key=f"reject_reason_{r['id']}",
                               label_visibility="collapsed", placeholder="Rejection reason (required)")
        if c3.button("Reject", key=f"reject_{r['id']}"):
            flash_and_rerun(rules.reject(store, user["id"], r["id"], reason))


def page_all_events(user):
    st.header("All requests and events")
    statuses = st.multiselect("Status", STATUSES, default=[rules.PENDING, rules.CONFIRMED],
                              format_func=str.title)
    for r in rules.list_requests(get_store()):
        if r["status"] not in statuses:
            continue
        box = request_card(r, show_requester=True)
        if r["status"] == rules.CONFIRMED:
            cancel_controls(box, user, r)


def page_venue_blocks(user):
    store = get_store()
    st.header("Venue blocks")
    st.caption("Block a venue for maintenance or renovation. "
               "A block cannot cover an existing pending or confirmed booking.")
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1, 2])
        venue = venue_picker(c1, "block_venue")
        kind = c2.selectbox("Reason", BLOCK_REASONS, key="block_kind")
        note = c3.text_input("Details (optional)", key="block_note")
        start, end = datetime_inputs("block", time(9, 0), time(18, 0))
        if st.button("Add block", type="primary"):
            reason = f"{kind}: {note.strip()}" if note.strip() else kind
            flash_and_rerun(rules.add_block(store, user["id"], venue["id"], start, end, reason))

    blocks = rules.list_blocks(store)
    st.subheader(f"Current blocks ({len(blocks)})")
    for b in blocks:
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"**{b['venue_name']}** · {window(b)} · {b['reason']}")
        if c2.button("Remove", key=f"remove_block_{b['id']}"):
            flash_and_rerun(rules.remove_block(store, user["id"], b["id"]))
