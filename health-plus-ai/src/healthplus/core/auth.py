"""Password hashing and account lookup for the app's login.

Accounts live in Streamlit secrets (local: .streamlit/secrets.toml, Cloud:
app Settings -> Secrets) as salted PBKDF2-SHA256 hashes — plain passwords
are never stored anywhere. Generate a hash with:

    python scripts/hash_password.py

Secrets format:

    [accounts.admin]
    name = "Hospital Admin"
    role = "admin"
    password_hash = "pbkdf2_sha256$600000$...$..."

    [accounts.reception]
    name = "Front Desk"
    role = "user"
    password_hash = "pbkdf2_sha256$600000$...$..."

Roles: "admin" (chat + admin panel) or "user" (chat only).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any, Mapping

_ALGORITHM = "pbkdf2_sha256"
# OWASP's current recommendation for PBKDF2-HMAC-SHA256.
_ITERATIONS = 600_000
ROLES = ("admin", "user")


@dataclass(frozen=True)
class Account:
    username: str
    name: str
    role: str
    password_hash: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def hash_password(password: str, *, iterations: int = _ITERATIONS) -> str:
    """Return an encoded salted hash: algorithm$iterations$salt$hash."""
    if not password:
        raise ValueError("Password must not be empty.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join(
        [_ALGORITHM, str(iterations), _b64(salt), _b64(digest)]
    )


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against an encoded hash in constant time."""
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = _unb64(salt_b64)
        expected = _unb64(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def load_accounts(raw: Mapping[str, Any] | None) -> dict[str, Account]:
    """Build accounts from the secrets `[accounts]` table, skipping bad rows."""
    accounts: dict[str, Account] = {}
    for username, entry in (raw or {}).items():
        try:
            role = str(entry.get("role", "user")).lower()
            password_hash = str(entry["password_hash"])
        except (AttributeError, KeyError):
            continue
        if role not in ROLES or not password_hash.startswith(_ALGORITHM + "$"):
            continue
        accounts[str(username).lower()] = Account(
            username=str(username).lower(),
            name=str(entry.get("name") or username),
            role=role,
            password_hash=password_hash,
        )
    return accounts


def authenticate(
    accounts: Mapping[str, Account], username: str, password: str
) -> Account | None:
    """Return the account for valid credentials, otherwise None.

    An unknown username still runs one hash, so response time does not
    reveal which usernames exist.
    """
    account = accounts.get(username.strip().lower())
    if account is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return account if verify_password(password, account.password_hash) else None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# Precomputed once so unknown-user checks cost the same as real ones.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
