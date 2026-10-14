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
    except (AttributeError, ValueError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)  # constant-time comparison
