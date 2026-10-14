"""JSON-file storage for the Campus Event Management System.

The whole database is one JSON document (data/events.json, or $EVENTS_DB).
Every write goes through Store.transaction(): it takes a lock, loads the
file, lets the caller check and change the data, then saves it atomically.
That keeps the "check, then write" in rules/ safe even if two Streamlit
sessions submit at the same moment.

This package stores data only; all business decisions live in rules/.
"""
import copy
import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = str(Path(__file__).resolve().parent.parent / "data" / "events.json")

# One lock per data file, shared by every Store object in this process,
# so separate browser sessions cannot interleave a check and a write.
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(path):
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(os.path.abspath(path), threading.RLock())


class Store:
    """One JSON file guarded by a lock. Seeds itself on first use."""

    def __init__(self, path=None):
        self.path = path or os.environ.get("EVENTS_DB", DEFAULT_PATH)
        self._lock = _lock_for(self.path)
        with self._lock:
            if not os.path.exists(self.path):
                self.reset()

    def reset(self):
        from db.seed import seed_data  # imported here so `python -m db.seed` runs cleanly

        with self._lock:
            self._save(seed_data())

    def read(self):
        """A snapshot of the data for display. Changes to it are not saved."""
        with self._lock:
            return self._load()

    @contextmanager
    def transaction(self):
        """Yield the data under the lock; save on exit only if it changed.

        If the block raises, nothing is saved.
        """
        with self._lock:
            data = self._load()
            before = copy.deepcopy(data)
            yield data
            if data != before:
                self._save(data)

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)  # atomic: never leaves a half-written file
