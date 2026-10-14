"""Initial campus data from the brief, plus staff accounts.

Reset the data file:  python -m db.seed --reset
"""
import argparse

from auth import hash_password
from db.repository import now


def seed_data():
    ts = now()
    return {
        # Staff accounts only. Attendees use the public view without logging in.
        # Demo passwords are listed in the README; only their hashes are stored.
        "users": [
            {"id": 1, "name": "Admin", "username": "admin", "role": "ADMIN",
             "password_hash": hash_password("admin123")},
            {"id": 2, "name": "Asha", "username": "asha", "role": "REQUESTER",
             "password_hash": hash_password("asha123")},
            {"id": 3, "name": "Ravi", "username": "ravi", "role": "REQUESTER",
             "password_hash": hash_password("ravi123")},
        ],
        "venues": [
            {"id": 1, "name": "Seminar Hall A", "type": "Seminar Hall", "capacity": 120},
            {"id": 2, "name": "Main Auditorium", "type": "Auditorium", "capacity": 500},
            {"id": 3, "name": "Conference Room C", "type": "Conference Room", "capacity": 40},
            {"id": 4, "name": "Central Amphitheatre", "type": "Open Venue", "capacity": 300},
            {"id": 5, "name": "Innovation Lab", "type": "Computer Lab", "capacity": 60},
        ],
        "blocks": [
            {
                "id": 1,
                "venue_id": 3,
                "start": "2026-08-04 09:00",
                "end": "2026-08-04 18:00",
                "reason": "Renovation",
                "created_by": 1,
            },
        ],
        "requests": [
            {
                "id": 1,
                "title": "AI Workshop",
                "event_type": "Technical Workshop",
                "requester_id": 2,
                "venue_id": 1,
                "attendance": 100,
                "start": "2026-08-04 10:00",
                "end": "2026-08-04 12:00",
                "status": "CONFIRMED",
                "decision_reason": None,
                "decided_by": 1,
                "created_at": ts,
                "updated_at": ts,
            },
            {
                "id": 2,
                "title": "Python Coding Bootcamp",
                "event_type": "Technical Workshop",
                "requester_id": 3,
                "venue_id": 5,
                "attendance": 50,
                "start": "2026-08-06 14:00",
                "end": "2026-08-06 17:00",
                "status": "CONFIRMED",
                "decision_reason": None,
                "decided_by": 1,
                "created_at": ts,
                "updated_at": ts,
            },
        ],
    }


if __name__ == "__main__":
    from db.connection import Store

    parser = argparse.ArgumentParser(description="Manage the events JSON store.")
    parser.add_argument("--reset", action="store_true", help="wipe and re-seed the data file")
    args = parser.parse_args()
    store = Store()
    if args.reset:
        store.reset()
        print(f"Reset and re-seeded {store.path}")
    else:
        print(f"Data file: {store.path}")
