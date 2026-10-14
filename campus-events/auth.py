"""Password hashing for staff logins (Admin and Requesters).

Uses salted PBKDF2-SHA256 from the standard library; plain passwords are never stored.
Attendees do not log in: the public view needs no account.
"""
import hashlib
import hmac
import secrets

ITERATIONS = 100_000


def hash_password(password):
    """Return 'salt$hash' (both hex) for storing in the data file."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
    except (AttributeError, ValueError):  # missing or damaged hash: never a match
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)  # constant-time comparison


# Checked when the username is unknown, so a failed login takes the same time
# whether or not the account exists (no guessing usernames from response time).
DUMMY_HASH = hash_password(secrets.token_hex(16))
