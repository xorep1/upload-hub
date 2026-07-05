"""Create or promote an admin user.

Usage:
    python -m scripts.create_admin <username> <phone> <password>
    python -m scripts.create_admin --promote <username_or_phone>

Run this from the project root after `alembic upgrade head`.
"""
import sys

from sqlalchemy import or_, select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User


def promote(identifier: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(or_(User.username == identifier, User.phone == identifier))
        )
        if not user:
            print(f"No user found matching '{identifier}'")
            sys.exit(1)
        user.is_admin = True
        db.add(user)
        db.commit()
        print(f"✅ {user.username} is now an admin.")


def create(username: str, phone: str, password: str) -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).where(or_(User.username == username, User.phone == phone))):
            print("A user with that username/phone already exists. Use --promote instead.")
            sys.exit(1)
        user = User(
            username=username,
            phone=phone,
            hashed_password=hash_password(password),
            is_phone_verified=True,
            is_admin=True,
        )
        db.add(user)
        db.commit()
        print(f"✅ Admin user '{username}' created.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--promote":
        promote(args[1])
    elif len(args) == 3:
        create(args[0], args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)
