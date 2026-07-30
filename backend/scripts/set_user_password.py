#!/usr/bin/env python3
"""
One-time helper to set/reset a user's password directly in the database.

Needed because the pre-auth "Lenin" account (id=1) was seeded with a
placeholder password hash by migration 002 - it owns whatever journals/
conversations/documents already existed before multi-user auth, but has no
usable login credential yet. Run this once to claim it, or to reset any
other account's password without going through email-based reset (which
isn't built yet).

Usage:
    python scripts/set_user_password.py <username_or_email> <new_password>

The password is read from argv, not typed into a prompt that might echo
to a shared terminal - run this on your own machine, not over someone
else's shell.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, select, or_
from sqlalchemy.orm import sessionmaker

from config import settings
from core_pkg.auth import hash_password
from models import User


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 1

    identifier, new_password = sys.argv[1], sys.argv[2]
    if len(new_password) < 8:
        print("Password must be at least 8 characters")
        return 1

    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        user = session.execute(
            select(User).where(or_(User.username == identifier, User.email == identifier))
        ).scalar_one_or_none()

        if not user:
            print(f"No user found matching '{identifier}'")
            return 1

        user.hashed_password = hash_password(new_password)
        session.commit()
        print(f"Password updated for {user.username} ({user.email})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
