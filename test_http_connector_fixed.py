#!/usr/bin/env python3
"""
Test the updated HTTP connector with hive_name parameter.
"""

from api.http_connector import list_recordings, test_connection
from api.database import SessionLocal
from api.models import FarmerDataSource, Hive

def main():
    db = SessionLocal()
    try:
        # Get the source for Hive 22 (which has audio files)
        hive_id = "1bf42b6b-c752-45dc-b618-e3b6b9784e0f"  # Hive 22
        
        source = db.query(FarmerDataSource).filter(
            FarmerDataSource.hive_id == hive_id
        ).first()
        
        if not source:
            print("Source not found!")
            return
        
        hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
        
        if not hive:
            print("Hive not found!")
            return
        
        print(f"Testing for Hive: {hive.hive_name} ({hive.hive_id})")
        print(f"API Key: {source.connection_config.get('api_key')}")
        print()
        
        # Test connection
        print("=" * 80)
        print("CONNECTION TEST")
        print("=" * 80)
        result = test_connection(source.connection_config)
        print(f"Result: {result}")
        print()
        
        # List recordings with hive_name
        print("=" * 80)
        print(f"LIST RECORDINGS FOR HIVE NAME: {hive.hive_name}")
        print("=" * 80)
        try:
            recordings = list_recordings(source.connection_config, hive_name=hive.hive_name)
            print(f"✓ Found {len(recordings)} recordings:")
            for rec in recordings:
                print(f"  - {rec}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
