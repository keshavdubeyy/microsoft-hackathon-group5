# Microsoft Hackathon – Group 5

**Campus Event Management System**: request a campus venue, get it reviewed by an Admin, and see confirmed events, with double bookings, capacity problems and venue blocks caught before a request is submitted.

```bash
cd campus-events
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py              # http://localhost:8501
```

Demo logins: `admin` / `admin123`, `asha` / `asha123`, `ravi` / `ravi123`. Attendees need no login.

Full documentation (architecture, business rules, assumptions, testing, pitch): **[campus-events/README.md](campus-events/README.md)**

Original plan (requirements, design, team split): **[campus-events/docs/plan.md](campus-events/docs/plan.md)**
