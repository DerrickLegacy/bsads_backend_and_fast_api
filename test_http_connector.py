#!/usr/bin/env python3
"""
Test the HTTP connector to see what the farmer's server is returning.
"""

from api.http_connector import list_recordings, test_connection
from api.database import SessionLocal
from api.models import FarmerDataSource

def main():
    db = SessionLocal()
    try:
        # Get one active source
        source = db.query(FarmerDataSource).filter(
            FarmerDataSource.is_active == True
        ).first()
        
        if not source:
            print("No active data sources found!")
            return
        
        print(f"Testing connection for hive: {source.hive_id}")
        print(f"Config: {source.connection_config}")
        print()
        
        # Test connection
        print("=" * 80)
        print("CONNECTION TEST")
        print("=" * 80)
        result = test_connection(source.connection_config)
        print(f"Result: {result}")
        print()
        
        # List recordings without hive_id filter
        print("=" * 80)
        print("LIST ALL RECORDINGS (no hive_id filter)")
        print("=" * 80)
        try:
            recordings = list_recordings(source.connection_config)
            print(f"Found {len(recordings)} recordings:")
            for rec in recordings[:10]:  # Show first 10
                print(f"  - {rec}")
            if len(recordings) > 10:
                print(f"  ... and {len(recordings) - 10} more")
        except Exception as e:
            print(f"Error: {e}")
        print()
        
        # List recordings with hive_id filter
        print("=" * 80)
        print(f"LIST RECORDINGS FOR HIVE: {source.hive_id}")
        print("=" * 80)
        try:
            recordings = list_recordings(source.connection_config, hive_id=str(source.hive_id))
            print(f"Found {len(recordings)} recordings:")
            for rec in recordings[:10]:
                print(f"  - {rec}")
            if len(recordings) > 10:
                print(f"  ... and {len(recordings) - 10} more")
        except Exception as e:
            print(f"Error: {e}")
        print()
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
