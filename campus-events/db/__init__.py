"""Data access layer: a single JSON file. No business rules here."""
from db.connection import DEFAULT_PATH, Store
from db.repository import find, next_id, now

__all__ = ["DEFAULT_PATH", "Store", "find", "next_id", "now"]
