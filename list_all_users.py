#!/usr/bin/env python3
"""List all users in the database"""

from api.database import SessionLocal
from api.models import User, Hive

db = SessionLocal()

print("=" * 80)
print("ALL USERS IN DATABASE")
print("=" * 80)

users = db.query(User).all()

print(f"\nTotal users: {len(users)}\n")

for i, user in enumerate(users, 1):
    hive_count = db.query(Hive).filter(Hive.owner_id == user.user_id, Hive.is_deleted == False).count()
    
    print(f"{i}. {user.full_name} ({user.email})")
    print(f"   Role: {user.role}")
    print(f"   User ID: {user.user_id}")
    print(f"   Phone: {user.phone}")
    print(f"   Hives: {hive_count}")
    print(f"   Server URL: {user.server_url}")
    print(f"   API Key: {user.api_key}")
    print(f"   Created: {user.created_at}")
    print()

print("=" * 80)
db.close()
