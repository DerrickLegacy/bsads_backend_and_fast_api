#!/usr/bin/env python3
"""Quick diagnostic to check data source status"""

from api.database import SessionLocal
from api.models import FarmerDataSource, Hive, User

db = SessionLocal()

print("=" * 80)
print("DATA SOURCE STATUS CHECK")
print("=" * 80)

# Get all users with credentials
users = db.query(User).filter(
    User.server_url.isnot(None),
    User.api_key.isnot(None)
).all()

print(f"\n📊 Users with server credentials: {len(users)}")
for user in users:
    print(f"  - {user.full_name} ({user.email})")
    print(f"    Server: {user.server_url}")
    print(f"    API Key: {user.api_key[:20]}...")

# Get all hives
hives = db.query(Hive).filter(Hive.is_deleted == False).all()
print(f"\n🐝 Total hives: {len(hives)}")

# Get all data sources
sources = db.query(FarmerDataSource).all()
print(f"\n📡 Total data sources: {len(sources)}")

for source in sources:
    hive = db.query(Hive).filter(Hive.hive_id == source.hive_id).first()
    user = db.query(User).filter(User.user_id == source.user_id).first()
    
    status = "✅ ACTIVE" if source.is_active else "❌ INACTIVE"
    print(f"\n{status}")
    print(f"  Source ID: {source.source_id}")
    print(f"  Hive: {hive.hive_name if hive else 'Unknown'} ({source.hive_id})")
    print(f"  Owner: {user.full_name if user else 'Unknown'}")
    print(f"  Type: {source.source_type}")
    print(f"  Path: {source.source_path}")
    print(f"  Config: {source.connection_config}")
    print(f"  Last Scanned: {source.last_scanned_at}")

# Count active vs inactive
active_count = db.query(FarmerDataSource).filter(FarmerDataSource.is_active == True).count()
inactive_count = db.query(FarmerDataSource).filter(FarmerDataSource.is_active == False).count()

print("\n" + "=" * 80)
print(f"SUMMARY: {active_count} active, {inactive_count} inactive")
print("=" * 80)

db.close()
