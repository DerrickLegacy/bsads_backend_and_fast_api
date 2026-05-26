#!/usr/bin/env python3
"""Check hive names for the active data sources."""

from api.database import SessionLocal
from api.models import FarmerDataSource, Hive

def main():
    db = SessionLocal()
    try:
        # Get the hive with audio files
        hive_id = "56a56deb-3b2f-4b16-8bfd-a29a9475627c"
        hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
        
        if hive:
            print(f"Hive ID: {hive.hive_id}")
            print(f"Hive Name: {hive.hive_name}")
            print(f"Owner ID: {hive.owner_id}")
            
            # Get the data source
            source = db.query(FarmerDataSource).filter(
                FarmerDataSource.hive_id == hive_id
            ).first()
            
            if source:
                print(f"\nData Source:")
                print(f"  API Key: {source.connection_config.get('api_key')}")
                print(f"  Active: {source.is_active}")
        
        print("\n" + "=" * 80)
        print("ALL ACTIVE HIVES WITH THEIR NAMES:")
        print("=" * 80)
        
        sources = db.query(FarmerDataSource).filter(
            FarmerDataSource.is_active == True
        ).all()
        
        for source in sources:
            hive = db.query(Hive).filter(Hive.hive_id == source.hive_id).first()
            if hive:
                api_key = source.connection_config.get('api_key', 'N/A')
                print(f"\nHive: {hive.hive_name}")
                print(f"  UUID: {hive.hive_id}")
                print(f"  API Key: {api_key}")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
