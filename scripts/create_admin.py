"""Create, promote, or seed users.

Usage:
    python -m scripts.create_admin <username> <phone> <password>
    python -m scripts.create_admin --promote <username_or_phone>
    python -m scripts.create_admin --seed <count>
    python -m scripts.create_admin --cleanup
    python -m scripts.create_admin --delete <user>

Run this from the project root after `alembic upgrade head`.
"""
import sys
from sqlalchemy import or_, select
from faker import Faker

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.user import User

def promote(identifier: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(or_(User.username == identifier, User.phone == identifier))
        )
        if not user:
            print(f"❌ No user found matching '{identifier}'")
            sys.exit(1)
        user.is_admin = True
        db.commit()
        print(f"✅ {user.username} is now an admin.")

def create(username: str, phone: str, password: str) -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).where(or_(User.username == username, User.phone == phone))):
            print("⚠️ User already exists. Use --promote instead.")
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

def seed(count: int) -> None:
    fake = Faker()
    print(f"⏳ Generating {count} fake users...")
    with SessionLocal() as db:
        users = [
            User(
                username=f"user_{i}_{fake.user_name()}",
                phone=fake.phone_number(),
                hashed_password=hash_password("password123"),
                is_phone_verified=True,
                is_admin=False
            ) for i in range(count)
        ]
        db.bulk_save_objects(users)
        db.commit()
        print(f"✅ {count} users created successfully.")

def cleanup() -> None:
    with SessionLocal() as db:
        confirm = input("⚠️ Are you sure? This will delete ALL non-admin users (y/n): ")
        if confirm.lower() == 'y':
            db.query(User).filter(User.is_admin == False).delete()
            db.commit()
            print("🧹 Cleanup completed.")
        else:
            print("Aborted.")
            
def delete(user_identifier: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(or_(User.username == user_identifier, User.id == user_identifier))
        )
        
        if not user:
            print(f"❌ '{user_identifier}'not found")
            return

        confirm = input("⚠️ Are you sure? This will delete user (y/n): ")
        if confirm.lower() == 'y':
            db.delete(user) 
            db.commit()
            print(f"🧹 user'{user.username}' deleted.")
        else:
            print("Aborted.")

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if len(args) == 2 and args[0] == "--promote":
        promote(args[1])
    elif len(args) == 2 and args[0] == "--seed":
        seed(int(args[1]))
    elif len(args) == 2 and args[0] == "--delete":
        delete(args[1])
    elif len(args) == 1 and args[0] == "--cleanup":
        cleanup()
    elif len(args) == 3:
        create(args[0], args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)