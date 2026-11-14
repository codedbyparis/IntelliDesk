"""Local account operations for the IntelliDesk demonstration app."""

import hashlib
import hmac
import re
import secrets
import sqlite3

from src.database import get_connection, now

PASSWORD_ITERATIONS = 600_000
PASSWORD_MIN_LENGTH = 12
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
_DUMMY_SALT = bytes.fromhex("6a7e8d130dc6c3a6999f537a8297e425")


def _validate_credentials(username, password):
    if not isinstance(username, str):
        raise ValueError(
            "Username must be 3–32 characters using letters, numbers, '.', '_' or '-'."
        )
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError(
            "Username must be 3–32 characters using letters, numbers, '.', '_' or '-'."
        )
    if not isinstance(password, str) or not PASSWORD_MIN_LENGTH <= len(password) <= 256:
        raise ValueError("Password must contain 12–256 characters.")
    return username


def _hash_password(password, salt, iterations=PASSWORD_ITERATIONS):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    ).hex()


def _create_account(username, password, role, db_path=None):
    username = _validate_credentials(username, password)
    if role not in ("user", "admin"):
        raise ValueError("Unknown account role.")
    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO users "
                "(username, password_salt, password_hash, iterations, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    username,
                    salt.hex(),
                    password_hash,
                    PASSWORD_ITERATIONS,
                    role,
                    now(),
                ),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("That username is already registered.") from error
    return {"id": cursor.lastrowid, "username": username, "role": role}


def register_user(username, password, db_path=None):
    """Create a regular account. Admin privileges cannot be self-registered."""
    return _create_account(username, password, "user", db_path)


def create_admin_account(username, password, db_path=None):
    """Provision an administrator from the trusted local command line."""
    return _create_account(username, password, "admin", db_path)


def authenticate_user(username, password, db_path=None):
    """Return a safe account summary on success, otherwise None."""
    username = username.strip() if isinstance(username, str) else ""
    if not username or not isinstance(password, str) or len(password) > 256:
        _hash_password("invalid-login", _DUMMY_SALT)
        return None

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT id, username, password_salt, password_hash, iterations, role "
            "FROM users WHERE username = ? COLLATE NOCASE",
            (username,),
        ).fetchone()

    if row is None:
        _hash_password(password, _DUMMY_SALT)
        return None

    candidate = _hash_password(
        password, bytes.fromhex(row["password_salt"]), row["iterations"]
    )
    if not hmac.compare_digest(candidate, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / "auth.db"
        from src.database import init_db

        init_db(database)
        user = register_user("sample.user", "a sufficiently long password", database)
        admin = create_admin_account("helpdesk.admin", "another sufficiently long password", database)
        assert authenticate_user("SAMPLE.USER", "a sufficiently long password", database) == user
        assert authenticate_user("sample.user", "incorrect password", database) is None
        assert authenticate_user("helpdesk.admin", "another sufficiently long password", database) == admin
    print("Local account checks passed.")
