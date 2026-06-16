#!/usr/bin/env python3
"""Update server URL for a user and all their hives"""

import sys
from api.database import SessionLocal
from api.models import FarmerDataSource, User

if len(sys.argv) < 3:
    print("Usage: python3 update_server_url.py <email> <new_server_url>")
    print("Example: python3 update_server_url.py user@example.com https://abc123.ngrok-free.dev")
    sys.exit(1)

email = sys.argv[1]
new_url = sys.argv[2].rstrip("/")

db = SessionLocal()

# Find user
user = db.query(User).filter(User.email == email).first()
if not user:
    print(f"❌ User not found: {email}")
    sys.exit(1)

print(f"Found user: {user.full_name} ({user.email})")
print(f"Old URL: {user.server_url}")
print(f"New URL: {new_url}")

# Update user's server URL
user.server_url = new_url
db.commit()
print("✅ Updated user's server URL")

# Update all data sources for this user's hives
sources = db.query(FarmerDataSource).filter(FarmerDataSource.user_id == user.user_id).all()
print(f"\nUpdating {len(sources)} data sources...")

for source in sources:
    if source.connection_config:
        source.connection_config["api_base_url"] = new_url
        source.source_path = new_url
        print(f"  ✅ Updated data source for hive {source.hive_id}")

db.commit()

print(f"\n✅ All done! Updated {len(sources)} data sources")
print(f"\nThe poller will now connect to: {new_url}")

db.close()
