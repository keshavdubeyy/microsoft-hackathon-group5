# Manual test run sheet

Run before the demo, in the browser, starting from fresh data (`python -m db.seed --reset`).
Automated equivalents run with `python -m pytest -q`.

| # | Who | Steps | Expected | Pass |
|---|---|---|---|---|
| T1 | asha, admin, public, asha | Asha: New request, Main Auditorium, 5 Aug 10:00–13:00, 300 people, Submit. Admin: Review queue, Approve. Log out: event shows under Confirmed events. Asha: My requests, Cancel event. | Pending → Confirmed → Cancelled; slot bookable again | ☐ |
| T2 | ravi | Seminar Hall A, 4 Aug 11:00–13:00 | Warning names "AI Workshop" 10:00–12:00; Submit disabled | ☐ |
| T3 | ravi | Seminar Hall A, 4 Aug 12:00–14:00 | Available (back-to-back allowed) | ☐ |
| T4 | ravi | Conference Room C, 4 Aug 14:00–15:00, 20 people | Warning: unavailable (Renovation) | ☐ |
| T5 | ravi | Innovation Lab, 200 people | Warning: exceeds capacity of 60 | ☐ |
| T6 | ravi | End time before start time | Warning: end must be after start | ☐ |
| T7 | asha, ravi | Asha submits a free slot; Ravi requests the same slot | Ravi sees "Clashes with a pending request" | ☐ |
| T8 | admin, ravi | Admin rejects Asha's T7 request with a reason; Ravi retries | Rejected with reason shown to Asha; Ravi can now submit | ☐ |
| T9 | asha | Requester sidebar | No Review queue / Approve available | ☐ |
| T10 | admin | Venue blocks: Seminar Hall A, 4 Aug 09:00–18:00 | Refused, lists "AI Workshop" | ☐ |
| L1 | public | Log in with admin / wrong password | "Invalid username or password"; stays on public view | ☐ |
| L2 | admin | Log out | Back to public Confirmed events view | ☐ |
