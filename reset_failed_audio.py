#!/usr/bin/env python3
"""
Reset failed audio sources back to pending so they can be reprocessed.
"""

from api.database import SessionLocal
from api.models import AudioSource

def main():
    db = SessionLocal()
    try:
        # Find any failed or processing audio sources
        failed = db.query(AudioSource).filter(
            AudioSource.status.in_(["failed", "processing"])
        ).all()
        
        if not failed:
            print("No failed or stuck audio sources found.")
            return
        
        print(f"Found {len(failed)} audio source(s) to reset:")
        for record in failed:
            print(f"  - {record.audio_id}: {record.status} -> pending")
            print(f"    URL: {record.source_url}")
            record.status = "pending"
        
        db.commit()
        print(f"\n✓ Reset {len(failed)} audio source(s) to pending status")
        print("The inference poller will reprocess them on the next run.")
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
