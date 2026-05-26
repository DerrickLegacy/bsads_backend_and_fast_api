#!/usr/bin/env python3
"""
Test script to verify the complete poller flow:
1. Check farmer's server for recordings
2. Manually trigger the scan_all_sources function
3. Check database for pending audio sources
4. Manually trigger process_pending_sources
5. Check for inference results
"""
import sys
import os

# Add the api directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.database import SessionLocal
from api.models import FarmerDataSource, AudioSource, InferenceResult
from api.poller import scan_all_sources, process_pending_sources
from api.http_connector import list_recordings

def check_active_data_sources():
    """Check which data sources are active."""
    print("=" * 60)
    print("STEP 1: Checking Active Data Sources")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        sources = db.query(FarmerDataSource).filter(FarmerDataSource.is_active == True).all()
        print(f"Found {len(sources)} active data source(s):\n")
        
        for source in sources:
            print(f"  Source ID: {source.source_id}")
            print(f"  Hive ID: {source.hive_id}")
            print(f"  Type: {source.source_type}")
            print(f"  Config: {source.connection_config}")
            print(f"  Last Scanned: {source.last_scanned_at}")
            print()
            
            # Try to list recordings
            if source.connection_config:
                try:
                    recordings = list_recordings(source.connection_config, hive_id=str(source.hive_id))
                    print(f"  ✓ API Connection Successful!")
                    print(f"  Found {len(recordings)} recording(s):")
                    for rec in recordings[:5]:  # Show first 5
                        print(f"    - {rec}")
                    if len(recordings) > 5:
                        print(f"    ... and {len(recordings) - 5} more")
                except Exception as e:
                    print(f"  ✗ API Connection Failed: {e}")
            print()
        
        return len(sources) > 0
    finally:
        db.close()

def run_discovery_scan():
    """Manually trigger the discovery scan."""
    print("=" * 60)
    print("STEP 2: Running Discovery Scan")
    print("=" * 60)
    
    try:
        scan_all_sources()
        print("✓ Discovery scan completed\n")
        return True
    except Exception as e:
        print(f"✗ Discovery scan failed: {e}\n")
        return False

def check_pending_audio_sources():
    """Check for pending audio sources in the database."""
    print("=" * 60)
    print("STEP 3: Checking Pending Audio Sources")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        pending = db.query(AudioSource).filter(AudioSource.status == "pending").all()
        print(f"Found {len(pending)} pending audio source(s):\n")
        
        for audio in pending[:10]:  # Show first 10
            print(f"  Audio ID: {audio.audio_id}")
            print(f"  Hive ID: {audio.hive_id}")
            print(f"  Source URL: {audio.source_url}")
            print(f"  Status: {audio.status}")
            print(f"  Ingested: {audio.ingestion_timestamp}")
            print()
        
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more\n")
        
        return len(pending) > 0
    finally:
        db.close()

def run_processing():
    """Manually trigger the processing of pending sources."""
    print("=" * 60)
    print("STEP 4: Processing Pending Audio Sources")
    print("=" * 60)
    
    try:
        process_pending_sources()
        print("✓ Processing completed\n")
        return True
    except Exception as e:
        print(f"✗ Processing failed: {e}\n")
        return False

def check_inference_results():
    """Check for recent inference results."""
    print("=" * 60)
    print("STEP 5: Checking Inference Results")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        results = db.query(InferenceResult).order_by(InferenceResult.created_at.desc()).limit(10).all()
        print(f"Found {len(results)} recent inference result(s):\n")
        
        for result in results:
            print(f"  Inference ID: {result.inference_id}")
            print(f"  Hive ID: {result.hive_id}")
            print(f"  Audio ID: {result.audio_id}")
            print(f"  Hive State: {result.hive_state}")
            print(f"  Confidence: {result.confidence_score}")
            print(f"  Analyzed: {result.analyzed_at}")
            print()
        
        return len(results) > 0
    finally:
        db.close()

def check_audio_source_status():
    """Check the status of all audio sources."""
    print("=" * 60)
    print("Audio Source Status Summary")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        from sqlalchemy import func
        
        status_counts = db.query(
            AudioSource.status,
            func.count(AudioSource.audio_id)
        ).group_by(AudioSource.status).all()
        
        print("Status breakdown:")
        for status, count in status_counts:
            print(f"  {status}: {count}")
        print()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("POLLER FLOW TEST")
    print("=" * 60 + "\n")
    
    # Step 1: Check active data sources
    if not check_active_data_sources():
        print("⚠ No active data sources found. Please configure a data source first.")
        sys.exit(1)
    
    # Step 2: Run discovery scan
    run_discovery_scan()
    
    # Step 3: Check pending audio sources
    has_pending = check_pending_audio_sources()
    
    if not has_pending:
        print("⚠ No pending audio sources found.")
        print("This means either:")
        print("  1. No new audio files are on the farmer's server")
        print("  2. All files have already been processed")
        print("\nTo add test files to the farmer's server:")
        print("  - Place .wav files in: recordings/<api_key>/<hive_id>/")
        print("  - Example: recordings/d3c07d19-cd0d-42b5-88e2-759349a4d023/b33556d2-7f30-4aac-ae38-9076925df80b/test.wav")
    else:
        # Step 4: Process pending sources
        print("⚠ Found pending sources. Skipping processing to avoid HuggingFace API calls.")
        print("To process them, uncomment the run_processing() call in the script.")
        # Uncomment the line below to actually process:
        # run_processing()
        
        # Step 5: Check inference results
        # check_inference_results()
    
    # Summary
    check_audio_source_status()
    
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
