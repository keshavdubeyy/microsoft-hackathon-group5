"""Admin pages: review queue, all events, venue blocks."""
from datetime import time

import streamlit as st

import rules
from ui.components import (
    STATUSES, datetime_inputs, flash_and_rerun, get_store, request_card, search_box, venue_picker, window,
)

BLOCK_REASONS = ["Maintenance", "Renovation", "Other operational restriction"]


def _review_details(box, store, r):
    """Decision aids shown on each pending request. Returns True if it is safe to approve."""
    d = rules.review_details(store, r["id"])
    m1, m2, m3 = box.columns(3)
    m1.metric("Venue capacity", d["capacity"], help=f"{d['venue_type']}; {r['attendance']} attendees expected")
    m2.metric("Duration", f"{d['duration_hours']} h")
    m3.metric("Requester history", f"{d['requester_confirmed']} confirmed",
              help=f"{d['requester_rejected']} rejected earlier")
    box.caption(f"Submitted {d['submitted_at']}")
    if d["conflicts"]:
        box.warning("Cannot approve yet:\n" + "\n".join(f"- {c}" for c in d["conflicts"]))
    else:
        box.info("No clashes with other bookings or venue blocks.")
    if d["same_day_schedule"]:
        with box.expander(f"Other bookings at {r['venue_name']} around this date"):
            st.dataframe(
                [{"Type": row["kind"], "When": window(row), "Details": row["title"]}
                 for row in d["same_day_schedule"]],
                hide_index=True, width="stretch",
            )
    return not d["conflicts"]


def page_review_queue(user):
    store = get_store()
    st.header("Review queue")
    text = search_box("review_search")
    queue = rules.search_requests(store, text, [rules.PENDING], recent_first=True)
    st.caption(f"{len(queue)} pending request(s), newest first. Pending requests hold their venue slot.")
    if not queue:
        st.info("No pending requests match your search." if text.strip()
                else "Nothing to review. New requests will appear here.")
    for r in queue:
        box = request_card(r, show_requester=True)
        can_approve = _review_details(box, store, r)
        c1, c2, c3 = box.columns([1, 3, 1])
        if c1.button("Approve", key=f"approve_{r['id']}", disabled=not can_approve):
            flash_and_rerun(rules.approve(store, user["id"], r["id"]))
        reason = c2.text_input("Rejection reason", key=f"reject_reason_{r['id']}",
                               label_visibility="collapsed",
                               placeholder="Rejection reason (required to reject)")
        # Reject stays disabled until a reason is typed (press Enter to apply it);
        # rules.reject still refuses an empty reason as the real safeguard.
        if c3.button("Reject", key=f"reject_{r['id']}", disabled=not reason.strip(),
                     help="Enter a rejection reason first" if not reason.strip() else None):
            flash_and_rerun(rules.reject(store, user["id"], r["id"], reason))


def page_all_events(user):
    store = get_store()
    st.header("All requests and events")
    c1, c2 = st.columns([3, 2])
    text = c1.text_input("Search", key="all_search", placeholder="Title, venue, requester, type or #id")
    statuses = c2.multiselect("Status", STATUSES, default=STATUSES, key="all_status",
                              format_func=str.title)
    rows = rules.search_requests(store, text, statuses, recent_first=True)
    st.caption(f"{len(rows)} request(s) shown.")
    if not rows:
        st.info("No requests match the search and status filter.")
        return
    # st.dataframe is read-only and has no row selection unless asked for.
    st.dataframe(
        [{"#": r["id"], "Event": r["title"], "Type": r["event_type"], "Venue": r["venue_name"],
          "When": window(r), "Attendees": r["attendance"], "Requested by": r["requester_name"],
          "Status": r["status"].title() + (" · NEW" if r["is_new"] else ""), "Reason": r["decision_reason"] or ""}
         for r in rows],
        hide_index=True, width="stretch",
    )

    confirmed = {r["id"]: r for r in rows if r["status"] == rules.CONFIRMED}
    if confirmed:
        with st.expander("Cancel a confirmed event"):
            event_id = st.selectbox(
                "Event", list(confirmed), key="cancel_event",
                format_func=lambda i: f"#{i} {confirmed[i]['title']} · {window(confirmed[i])}",
            )
            reason = st.text_input("Cancellation reason (optional)", key="cancel_reason")
            if st.button("Cancel event", key="cancel_selected"):
                flash_and_rerun(rules.cancel(store, user["id"], event_id, reason))


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
