"""Password hashing and session cookies for Campus Customs.

Passwords are stored only as PBKDF2-HMAC-SHA256 digests in the format the seeded
`users` rows already use:

    pbkdf2_sha256$<salt>$<hex digest>

The plaintext password is never written to the database, never logged, and never
returned by any endpoint. Verification re-derives the digest from the submitted
password and the stored salt and compares the two in constant time.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

ALGORITHM = "pbkdf2_sha256"
# Matches the iteration count used for the seeded accounts, so the existing
# test user keeps working without a re-hash.
ITERATIONS = 120_000
DKLEN = 32
SALT_BYTES = 8  # 16 hex characters, like the seeded rows

SESSION_COOKIE = "cc_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # one week

_SECRET_FILE = Path(__file__).resolve().parent / ".session_secret"


def _session_secret() -> bytes:
    """Key used to sign session cookies.

    Taken from the environment when set; otherwise generated once and kept in a
    gitignored file so sessions survive a server restart.
    """
    env = os.environ.get("CAMPUS_CUSTOMS_SECRET")
    if env:
        return env.encode()
    if not _SECRET_FILE.exists():
        _SECRET_FILE.write_text(secrets.token_hex(32))
        _SECRET_FILE.chmod(0o600)
    return _SECRET_FILE.read_text().strip().encode()


# ---------------------------------------------------------------- passwords

def hash_password(password: str) -> str:
    """Return `pbkdf2_sha256$<salt>$<digest>` for a new or changed password."""
    salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS, dklen=DKLEN
    ).hex()
    return f"{ALGORITHM}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Check a submitted password against a stored hash, in constant time."""
    try:
        algorithm, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS, dklen=DKLEN
    ).hex()
    return hmac.compare_digest(candidate, digest)


# ----------------------------------------------------------------- sessions

def issue_session(user_id: int) -> str:
    """Sign a `<user_id>.<expiry>` pair so the cookie cannot be forged."""
    expires = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{user_id}.{expires}"
    signature = hmac.new(_session_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session(token: str | None) -> int | None:
    """Return the user id in a valid, unexpired cookie, else None."""
    if not token:
        return None
    try:
        user_id, expires, signature = token.rsplit(".", 2)
    except ValueError:
        return None
    payload = f"{user_id}.{expires}"
    expected = hmac.new(_session_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        if int(expires) < time.time():
            return None
        return int(user_id)
    except ValueError:
        return None
