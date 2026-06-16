#!/usr/bin/env python3
"""Check actual hives in the database"""

from api.database import SessionLocal
from api.models import FarmerDataSource, Hive, User

db = SessionLocal()

print("=" * 80)
print("ACTUAL HIVES IN DATABASE")
print("=" * 80)

# Get all users
users = db.query(User).all()

for user in users:
    hives = db.query(Hive).filter(Hive.owner_id == user.user_id, Hive.is_deleted == False).all()
    
    if not hives:
        continue
    
    print(f"\n👤 {user.full_name} ({user.email})")
    print(f"   Server: {user.server_url}")
    print(f"   API Key: {user.api_key}")
    print(f"   Hives ({len(hives)}):")
    
    for hive in hives:
        source = db.query(FarmerDataSource).filter(FarmerDataSource.hive_id == hive.hive_id).first()
        
        status = "✅ ACTIVE" if source and source.is_active else "❌ INACTIVE"
        
        print(f"\n   {status} {hive.hive_name}")
        print(f"      ID: {hive.hive_id}")
        print(f"      Location: {hive.hive_location}")
        print(f"      Type: {hive.hive_type}")
        print(f"      State: {hive.current_state}")
        
        if source:
            print(f"      Data Source: {source.source_id}")
            print(f"      Server Path: {source.source_path}")
            print(f"      Last Scanned: {source.last_scanned_at}")

print("\n" + "=" * 80)
db.close()
