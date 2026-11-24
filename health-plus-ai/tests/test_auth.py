"""Login building blocks: hashing, verification, account loading."""

from __future__ import annotations

from healthplus.core.auth import authenticate, hash_password, load_accounts, verify_password

# Low iteration count keeps the test suite fast; production uses 600k.
FAST = 1_000


def test_hash_is_salted_and_verifies():
    a = hash_password("correct horse battery", iterations=FAST)
    b = hash_password("correct horse battery", iterations=FAST)
    assert a != b  # random salt
    assert a.startswith("pbkdf2_sha256$1000$")
    assert verify_password("correct horse battery", a)
    assert not verify_password("wrong password", a)


def test_malformed_hash_never_verifies():
    for bad in ["", "plain-text-password", "md5$1$x$y", "pbkdf2_sha256$x$y"]:
        assert not verify_password("anything", bad)


def test_load_accounts_skips_invalid_rows_and_normalises_usernames():
    raw = {
        "Admin": {"role": "admin", "name": "Boss", "password_hash": hash_password("pw-admin-123", iterations=FAST)},
        "desk": {"role": "user", "password_hash": hash_password("pw-desk-1234", iterations=FAST)},
        "noHash": {"role": "user"},
        "badRole": {"role": "root", "password_hash": hash_password("x" * 12, iterations=FAST)},
        "plain": {"role": "user", "password_hash": "letmein"},
    }
    accounts = load_accounts(raw)
    assert set(accounts) == {"admin", "desk"}
    assert accounts["admin"].is_admin and accounts["admin"].name == "Boss"
    assert not accounts["desk"].is_admin and accounts["desk"].name == "desk"


def test_authenticate():
    accounts = load_accounts(
        {"desk": {"role": "user", "password_hash": hash_password("pw-desk-1234", iterations=FAST)}}
    )
    assert authenticate(accounts, " DESK ", "pw-desk-1234").username == "desk"
    assert authenticate(accounts, "desk", "nope") is None
    assert authenticate(accounts, "ghost", "pw-desk-1234") is None


def test_no_accounts_configured():
    assert load_accounts(None) == {}
    assert authenticate({}, "admin", "anything") is None
