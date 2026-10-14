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


def demo_requests():
    """Extra requests in every status, so the Admin pages have something to review.

    Not part of the brief's initial data; load with `python -m db.seed --reset --demo`.
    """
    ts = now()

    def req(id, title, event_type, requester_id, venue_id, attendance, start, end,
            status="PENDING", reason=None):
        decided = status != "PENDING"
        return {
            "id": id, "title": title, "event_type": event_type, "requester_id": requester_id,
            "venue_id": venue_id, "attendance": attendance, "start": start, "end": end,
            "status": status, "decision_reason": reason, "decided_by": 1 if decided else None,
            "created_at": ts, "updated_at": ts,
        }

    return [
        req(3, "Campus Hackathon 2026", "Hackathon", 2, 2, 400,
            "2026-08-08 09:00", "2026-08-09 18:00"),
        req(4, "Placement Drive Briefing", "Placement Session", 3, 1, 110,
            "2026-08-04 12:00", "2026-08-04 14:00"),
        req(5, "Robotics Club Demo", "Club Activity", 2, 5, 45,
            "2026-08-07 10:00", "2026-08-07 12:00"),
        req(6, "Cultural Night Rehearsal", "Cultural Programme", 3, 4, 250,
            "2026-08-10 17:00", "2026-08-10 21:00"),
        req(7, "Inter-College Quiz", "Student Competition", 2, 1, 90,
            "2026-08-11 14:00", "2026-08-11 16:00", "CONFIRMED"),
        req(8, "Open Mic Evening", "Cultural Programme", 3, 4, 200,
            "2026-08-12 18:00", "2026-08-12 20:00", "REJECTED", "Amphitheatre needed for stage setup"),
        req(9, "Resume Workshop", "Technical Workshop", 2, 3, 30,
            "2026-08-13 10:00", "2026-08-13 12:00", "CANCELLED", "Speaker unavailable"),
    ]


if __name__ == "__main__":
    from db.connection import Store

    parser = argparse.ArgumentParser(description="Manage the events JSON store.")
    parser.add_argument("--reset", action="store_true", help="wipe and re-seed the data file")
    parser.add_argument("--demo", action="store_true",
                        help="with --reset, also add pending/rejected/cancelled demo requests")
    args = parser.parse_args()
    store = Store()
    if args.reset:
        store.reset()
        if args.demo:
            with store.transaction() as data:
                data["requests"].extend(demo_requests())
        print(f"Reset and re-seeded {store.path}")
    else:
        print(f"Data file: {store.path}")
