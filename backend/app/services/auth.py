"""Password hashing and login tokens, using only the standard library.

Passwords are hashed with scrypt and a random salt. Login tokens are random 256-bit
strings; only their SHA-256 hash is stored, so a database leak doesn't expose sessions.
"""

import datetime as dt
import hashlib
import hmac
import secrets

TOKEN_LIFETIME = dt.timedelta(days=90)
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def new_token() -> tuple[str, str]:
    """Return (token to give the client, hash to store)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_expiry() -> dt.datetime:
    return dt.datetime.now(dt.UTC) + TOKEN_LIFETIME
