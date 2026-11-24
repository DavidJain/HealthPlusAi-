"""Create a login account entry for the HealthPlus app.

Prompts for a username, role, and password (hidden while typing) and prints
a block to paste into Streamlit secrets:
  - locally: .streamlit/secrets.toml (git-ignored)
  - on Streamlit Cloud: app Settings -> Secrets

Usage:  python scripts/hash_password.py
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthplus.core.auth import ROLES, hash_password  # noqa: E402


def main() -> int:
    username = input("Username (letters, digits, _ or -): ").strip().lower()
    if not username or not all(c.isalnum() or c in "_-" for c in username):
        print("Invalid username.")
        return 1
    name = input("Display name: ").strip() or username
    role = input(f"Role {ROLES} [user]: ").strip().lower() or "user"
    if role not in ROLES:
        print(f"Role must be one of {ROLES}.")
        return 1
    password = getpass.getpass("Password (min 10 characters): ")
    if len(password) < 10:
        print("Password must be at least 10 characters.")
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.")
        return 1

    print("\nPaste this into your Streamlit secrets:\n")
    print(f"[accounts.{username}]")
    print(f'name = "{name}"')
    print(f'role = "{role}"')
    print(f'password_hash = "{hash_password(password)}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
