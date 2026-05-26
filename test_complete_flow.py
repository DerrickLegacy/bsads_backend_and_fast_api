#!/usr/bin/env python3
"""
Test the complete poller flow manually.
"""

from api.database import SessionLocal
from api.models import AudioSource
from api.poller import scan_all_sources

def main():
    print("=" * 80)
    print("TESTING COMPLETE POLLER FLOW")
    print("=" * 80)
    print()
    
    # Check current state
    db = SessionLocal()
    before_count = db.query(AudioSource).count()
    print(f"AudioSource records before scan: {before_count}")
    db.close()
    
    # Run the discovery poller manually
    print("\nRunning discovery poller...")
    print("-" * 80)
    scan_all_sources()
    print("-" * 80)
    
    # Check after state
    db = SessionLocal()
    after_count = db.query(AudioSource).count()
    pending_count = db.query(AudioSource).filter(AudioSource.status == "pending").count()
    
    print(f"\nAudioSource records after scan: {after_count}")
    print(f"Pending records: {pending_count}")
    print(f"New records discovered: {after_count - before_count}")
    
    if after_count > before_count:
        print("\n✓ SUCCESS! Discovery poller found new audio files!")
        
        # Show the new records
        new_records = db.query(AudioSource).filter(
            AudioSource.status == "pending"
        ).limit(5).all()
        
        print("\nNew audio sources:")
        for record in new_records:
            print(f"  - {record.source_url}")
            print(f"    Status: {record.status}")
            print(f"    Hive ID: {record.hive_id}")
    else:
        print("\n⚠️  No new files discovered. Check:")
        print("  1. Are there audio files in the farmer's server?")
        print("  2. Are the API keys valid?")
        print("  3. Check the logs above for errors")
    
    db.close()

if __name__ == "__main__":
    main()
