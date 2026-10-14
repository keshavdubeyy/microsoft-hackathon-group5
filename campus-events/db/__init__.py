"""Data access layer: a single JSON file. No business rules here.

Storage and locking live in db.connection; db.repository has small helpers.
Read-only list/filter queries for the UI live in rules/queries.py.
"""
from db.connection import DEFAULT_PATH, Store
from db.repository import find, next_id, now

__all__ = ["DEFAULT_PATH", "Store", "find", "next_id", "now"]
