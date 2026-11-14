"""Provision a local IntelliDesk administrator from a trusted terminal."""

from getpass import getpass

from src.auth import create_admin_account
from src.database import init_db


def main():
    init_db()
    username = input("Admin username: ")
    password = getpass("Admin password (12+ characters): ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        account = create_admin_account(username, password)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"Administrator account {account['username']!r} created.")


if __name__ == "__main__":
    main()
