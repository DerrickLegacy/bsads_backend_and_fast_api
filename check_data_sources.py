#!/usr/bin/env python3
"""
Diagnostic script to check FarmerDataSource and AudioSource records.
Run this to see why the poller isn't working.
"""

from api.database import SessionLocal
from api.models import FarmerDataSource, AudioSource, Hive, User

def main():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("FARMER DATA SOURCES")
        print("=" * 80)
        
        sources = db.query(FarmerDataSource).all()
        if not sources:
            print("❌ No FarmerDataSource records found!")
            print("\nThis means no hives are configured for polling.")
            print("The poller needs at least one active data source to work.\n")
        else:
            for source in sources:
                hive = db.query(Hive).filter(Hive.hive_id == source.hive_id).first()
                user = db.query(User).filter(User.user_id == source.user_id).first()
                
                print(f"\nSource ID: {source.source_id}")
                print(f"  Hive: {hive.hive_name if hive else 'Unknown'} ({source.hive_id})")
                print(f"  User: {user.email if user else 'Unknown'}")
                print(f"  Type: {source.source_type}")
                print(f"  Active: {'✓ YES' if source.is_active else '❌ NO'}")
                print(f"  Last Scanned: {source.last_scanned_at or 'Never'}")
                print(f"  Connection Config: {source.connection_config}")
                
                if not source.is_active:
                    print("  ⚠️  INACTIVE - Poller will skip this source!")
                    if not source.connection_config:
                        print("     Reason: No connection config (api_base_url/api_key)")
        
        print("\n" + "=" * 80)
        print("AUDIO SOURCES")
        print("=" * 80)
        
        audio_sources = db.query(AudioSource).all()
        if not audio_sources:
            print("❌ No AudioSource records found!")
            print("\nThis means the discovery poller hasn't found any audio files yet.")
        else:
            print(f"\nTotal: {len(audio_sources)} records")
            
            by_status = {}
            for record in audio_sources:
                by_status[record.status] = by_status.get(record.status, 0) + 1
            
            for status, count in by_status.items():
                print(f"  {status}: {count}")
            
            print("\nRecent records:")
            for record in audio_sources[:5]:
                print(f"  - {record.source_url} [{record.status}]")
        
        print("\n" + "=" * 80)
        print("USERS WITH SERVER CREDENTIALS")
        print("=" * 80)
        
        users = db.query(User).filter(User.server_url.isnot(None)).all()
        if not users:
            print("❌ No users have server_url configured!")
            print("\nUsers need to set server_url and api_key for auto-configuration.")
        else:
            for user in users:
                print(f"\n{user.email}:")
                print(f"  Server URL: {user.server_url}")
                print(f"  API Key: {user.api_key[:8]}..." if user.api_key else "  API Key: None")
        
        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        
        active_sources = [s for s in sources if s.is_active]
        if not active_sources:
            print("\n❌ NO ACTIVE DATA SOURCES")
            print("\nThe poller is running but has nothing to scan.")
            print("\nTo fix this:")
            print("1. Make sure users have server_url and api_key configured")
            print("2. Or manually configure data sources via POST /hives/{hive_id}/data-source/configure")
            print("3. Check that connection tests are passing")
        else:
            print(f"\n✓ {len(active_sources)} active data source(s)")
            print("\nThe poller should be scanning these sources every 30 seconds.")
            print("If no audio files are being discovered, check:")
            print("1. The farmer's server is running and accessible")
            print("2. Audio files exist in the correct location")
            print("3. The API key has permission to list recordings")
        
        print()
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
