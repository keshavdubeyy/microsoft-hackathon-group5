"""Admin-only housekeeping: resetting the demo data."""
import logging

from db import find
from db.seed import seed_data
from rules.models import ADMIN, Result

log = logging.getLogger("rules")


def reset_demo_data(store, user_id):
    """Admin wipes every request and block and restores the initial campus data."""
    with store.transaction() as data:
        user = find(data["users"], user_id)
        if user is None or user["role"] != ADMIN:
            return Result(False, "Only an Admin can reset the demo data.")
        data.clear()
        data.update(seed_data())
        log.info("user=%s reset the demo data", user["name"])
        return Result(True, "Demo data reset to the initial campus data.")
