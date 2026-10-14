"""Small lookup helpers over the in-memory data (lists of dicts).

List/filter queries used by the UI live in rules/queries.py, not here.
"""
from datetime import datetime


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def next_id(items):
    return max((item["id"] for item in items), default=0) + 1


def find(items, item_id):
    return next((item for item in items if item["id"] == item_id), None)
