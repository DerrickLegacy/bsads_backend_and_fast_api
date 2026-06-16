#!/usr/bin/env python3
"""Manually activate data sources after fixing connection issues"""

from api.database import SessionLocal
from api.models import FarmerDataSource
from api.http_connector import test_connection

db = SessionLocal()

print("=" * 80)
print("DATA SOURCE ACTIVATION")
print("=" * 80)

# Get all inactive data sources
sources = db.query(FarmerDataSource).filter(FarmerDataSource.is_active == False).all()

print(f"\nFound {len(sources)} inactive data sources\n")

for source in sources:
    print(f"Testing connection for source {source.source_id}...")
    print(f"  URL: {source.source_path}")
    
    if not source.connection_config:
        print("  ❌ No connection config - skipping")
        continue
    
    # Test the connection
    result = test_connection(source.connection_config)
    
    if result.get("ok"):
        print(f"  ✅ Connection successful - activating")
        source.is_active = True
        db.commit()
    else:
        error = result.get("error", "Unknown error")
        print(f"  ❌ Connection failed: {error}")
        print(f"     Data source will remain inactive")

print("\n" + "=" * 80)

# Summary
active_count = db.query(FarmerDataSource).filter(FarmerDataSource.is_active == True).count()
inactive_count = db.query(FarmerDataSource).filter(FarmerDataSource.is_active == False).count()

print(f"FINAL STATUS: {active_count} active, {inactive_count} inactive")
print("=" * 80)

db.close()
