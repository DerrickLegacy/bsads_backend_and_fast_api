"""
Conditions Poller - Fetches and processes CSV condition data from external data sources.

Architecture:
- Device → Simulation Server (uploads CSV instantly, device sleeps)
- Backend polls simulation server periodically
- Uses queue/concurrency to handle traffic bursts
- Implements deduplication (hive_id + recorded_at)

Pattern:
- Follows same architecture as poller_concurrent.py for audio files
- Concurrent processing with batching
- Proper error handling and recovery
"""

import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import AudioSource, Hive, HiveCondition, User
from api.system_logger import exc_details, log_standalone

# Concurrency settings
MAX_WORKERS = 5  # Concurrent CSV processing workers


# ---------------------------------------------------------------------------
# Main Poller Function
# ---------------------------------------------------------------------------

def poll_and_process_conditions() -> None:
    """
    Main entry point for conditions poller.
    
    1. Fetches list of CSV files from each active farmer's simulation server
    2. Downloads and processes each CSV file
    3. Implements deduplication based on hive_id + recorded_at
    4. Uses concurrent processing for scalability
    """
    db: Session = SessionLocal()
    try:
        # Get all active farmers with server credentials
        farmers = (
            db.query(User)
            .filter(
                User.role == "farmer",
                User.server_url.isnot(None),
                User.api_key.isnot(None)
            )
            .all()
        )
        
        if not farmers:
            log_standalone("info", "conditions_poller",
                           "No farmers with server credentials found")
            return
        
        log_standalone("info", "conditions_poller",
                       f"🌡️  Conditions poller: processing {len(farmers)} farmers")
        
        success_count = 0
        error_count = 0
        
        # Process farmers concurrently
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_farmer = {
                executor.submit(_process_farmer_conditions_safe, farmer): farmer
                for farmer in farmers
            }
            
            for future in as_completed(future_to_farmer):
                farmer = future_to_farmer[future]
                try:
                    result = future.result()
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as exc:
                    error_count += 1
                    log_standalone("error", "conditions_poller",
                                   f"Unexpected error processing farmer {farmer.user_id}: {exc}",
                                   user_id=str(farmer.user_id),
                                   details=exc_details(exc))
        
        log_standalone("info", "conditions_poller",
                       f"✓ Conditions poller: completed ({success_count} success, {error_count} errors)")
    
    except Exception as exc:
        log_standalone("error", "conditions_poller",
                       f"poll_and_process_conditions failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()


def _process_farmer_conditions_safe(farmer: User) -> bool:
    """
    Process conditions for a single farmer with its own DB session.
    Returns True on success, False on error.
    """
    db: Session = SessionLocal()
    try:
        # Get farmer's hives
        hives = (
            db.query(Hive)
            .filter(
                Hive.owner_id == farmer.user_id,
                Hive.is_deleted == False
            )
            .all()
        )
        
        if not hives:
            log_standalone("info", "conditions_poller",
                           f"No hives found for farmer {farmer.email}",
                           user_id=str(farmer.user_id))
            return True
        
        total_processed = 0
        total_new = 0
        total_duplicate = 0
        
        # Process each hive
        for hive in hives:
            if not hive.hive_name:
                continue
            
            try:
                stats = _fetch_and_process_conditions(
                    farmer=farmer,
                    hive=hive,
                    db=db
                )
                total_processed += stats['processed']
                total_new += stats['new']
                total_duplicate += stats['duplicate']
            
            except Exception as exc:
                log_standalone("error", "conditions_poller",
                               f"Failed to process conditions for hive {hive.hive_name}: {exc}",
                               user_id=str(farmer.user_id),
                               hive_id=str(hive.hive_id),
                               details=exc_details(exc))
                continue
        
        if total_processed > 0:
            log_standalone("info", "conditions_poller",
                           f"✓ Farmer {farmer.email}: {total_new} new, {total_duplicate} duplicate from {total_processed} records",
                           user_id=str(farmer.user_id))
        
        return True
    
    except Exception as exc:
        log_standalone("error", "conditions_poller",
                       f"Failed to process farmer conditions: {exc}",
                       user_id=str(farmer.user_id),
                       details=exc_details(exc))
        return False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CSV Fetching and Processing
# ---------------------------------------------------------------------------

def _fetch_and_process_conditions(farmer: User, hive: Hive, db: Session) -> Dict[str, int]:
    """
    Fetch and process condition CSV files for a specific hive.
    
    Returns:
        {"processed": int, "new": int, "duplicate": int}
    """
    # Build config like in poller_concurrent.py
    config = {
        "api_base_url": farmer.server_url,
        "api_key": farmer.api_key
    }
    
    hive_name = hive.hive_name
    
    # List CSV files using http_connector (handles localhost translation)
    from api.http_connector import list_conditions, download_condition_file, delete_condition_file
    
    try:
        csv_files = list_conditions(config, hive_name)
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 404:
            # Endpoint doesn't exist or no files found - not an error
            return {"processed": 0, "new": 0, "duplicate": 0}
        log_standalone("warning", "conditions_poller",
                       f"Failed to list conditions: {exc.response.status_code}",
                       hive_id=str(hive.hive_id))
        raise
    except Exception as exc:
        log_standalone("error", "conditions_poller",
                       f"Failed to list conditions for hive {hive_name}: {exc}",
                       hive_id=str(hive.hive_id),
                       details=exc_details(exc))
        raise
    
    if not csv_files:
        return {"processed": 0, "new": 0, "duplicate": 0}
    
    log_standalone("info", "conditions_poller",
                   f"Found {len(csv_files)} CSV files for hive {hive_name}",
                   hive_id=str(hive.hive_id))
    
    total_stats = {"processed": 0, "new": 0, "duplicate": 0}
    
    # Process each CSV file
    for csv_file in csv_files:
        try:
            csv_content = download_condition_file(config, csv_file)
            
            stats = _process_csv_content(
                csv_content=csv_content,
                hive=hive,
                db=db
            )
            total_stats['processed'] += stats['processed']
            total_stats['new'] += stats['new']
            total_stats['duplicate'] += stats['duplicate']
            
            # Delete the file after successful processing
            delete_result = delete_condition_file(config, csv_file)
            if delete_result['ok']:
                log_standalone("info", "conditions_poller",
                               f"Successfully deleted file {csv_file}",
                               hive_id=str(hive.hive_id))
            else:
                log_standalone("warning", "conditions_poller",
                               f"Failed to delete file {csv_file}: {delete_result['error']}",
                               hive_id=str(hive.hive_id))
            
        except Exception as exc:
            log_standalone("error", "conditions_poller",
                           f"Failed to process CSV file {csv_file}: {exc}",
                           hive_id=str(hive.hive_id),
                           details=exc_details(exc))
            continue
    
    return total_stats


def _process_csv_content(
    csv_content: str,
    hive: Hive,
    db: Session
) -> Dict[str, int]:
    """
    Process CSV content and insert records with deduplication.
    
    Handles two CSV formats:
    1. With headers: Date,Temperature,Humidity
    2. Without headers (actual data format): "datetime","temp*brood*ext","hum*brood*ext",...
    
    Temperature format: honey*brood*exterior
    Humidity format: honey*brood*exterior
    
    Returns:
        {"processed": int, "new": int, "duplicate": int}
    """
    # Log CSV content for debugging
    log_standalone("info", "conditions_poller",
                   f"CSV content length: {len(csv_content)} chars",
                   hive_id=str(hive.hive_id),
                   details={"csv_sample": csv_content[:500] if csv_content else "empty"})
    
    # Parse CSV - check if it has headers
    try:
        lines = csv_content.strip().split('\n')
        if not lines:
            return {"processed": 0, "new": 0, "duplicate": 0}
        
        # Check if first line looks like headers
        first_line = lines[0].strip()
        has_headers = 'Date' in first_line and 'Temperature' in first_line and 'Humidity' in first_line
        
        if has_headers:
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            log_standalone("info", "conditions_poller",
                           f"CSV with headers: {csv_reader.fieldnames}",
                           hive_id=str(hive.hive_id))
        else:
            # No headers - use csv.reader and map columns manually
            csv_reader = csv.reader(io.StringIO(csv_content))
            log_standalone("info", "conditions_poller",
                           "CSV without headers - using manual column mapping",
                           hive_id=str(hive.hive_id))
        
    except Exception as exc:
        raise Exception(f"Failed to parse CSV: {exc}")
    
    records_processed = 0
    records_new = 0
    records_duplicate = 0
    
    # Batch processing for efficiency
    new_conditions = []
    
    for row in csv_reader:
        records_processed += 1
        log_standalone("info", "conditions_poller",
                       f"Processing row {records_processed}: {row}",
                       hive_id=str(hive.hive_id))
        
        try:
            # Parse date and values based on format
            if has_headers:
                # Format 1: with headers (DictReader)
                date_str = row['Date']
                temp_str = row['Temperature']
                humidity_str = row['Humidity']
            else:
                # Format 2: without headers (list format)
                # Format: ["datetime", "temp*brood*ext", "hum*brood*ext", ...]
                if len(row) < 3:
                    raise ValueError(f"Row has only {len(row)} columns, need at least 3")
                date_str = row[0].strip('"')  # Remove quotes if present
                temp_str = row[1].strip('"')
                humidity_str = row[2].strip('"')
            
            # Parse date
            recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            
            # Check if record already exists (deduplication)
            existing = db.query(HiveCondition).filter(
                HiveCondition.hive_id == hive.hive_id,
                HiveCondition.recorded_at == recorded_at
            ).first()
            
            if existing:
                records_duplicate += 1
                log_standalone("info", "conditions_poller",
                               f"Skipping duplicate record at {recorded_at}",
                               hive_id=str(hive.hive_id))
                continue  # Skip duplicate record
            
            # Parse temperature (honey*brood*exterior)
            temps = temp_str.split('*')
            if len(temps) != 3:
                raise ValueError(f"Temperature must have 3 values separated by *, got: '{temp_str}'")
            temp_honey, temp_brood, temp_exterior = [float(t) for t in temps]
            
            # Parse humidity (honey*brood*exterior)
            humidities = humidity_str.split('*')
            if len(humidities) != 3:
                raise ValueError(f"Humidity must have 3 values separated by *, got: '{humidity_str}'")
            humidity_honey, humidity_brood, humidity_exterior = [float(h) for h in humidities]
            
            # Try to find matching audio file by timestamp
            audio = db.query(AudioSource).filter(
                AudioSource.hive_id == hive.hive_id,
                AudioSource.captured_at == recorded_at
            ).first()
            
            # Create condition record
            condition = HiveCondition(
                hive_id=hive.hive_id,
                audio_id=audio.audio_id if audio else None,
                temp_honey=temp_honey,
                temp_brood=temp_brood,
                temp_exterior=temp_exterior,
                humidity_honey=humidity_honey,
                humidity_brood=humidity_brood,
                humidity_exterior=humidity_exterior,
                recorded_at=recorded_at
            )
            
            new_conditions.append(condition)
            records_new += 1
            log_standalone("info", "conditions_poller",
                           f"Added new record for {recorded_at}: temp={temp_honey}/{temp_brood}/{temp_exterior}, humidity={humidity_honey}/{humidity_brood}/{humidity_exterior}",
                           hive_id=str(hive.hive_id))
        
        except Exception as exc:
            # Log error but continue processing other rows
            log_standalone("warning", "conditions_poller",
                           f"Error processing CSV row {records_processed}: {exc}",
                           hive_id=str(hive.hive_id),
                           details={"row": row, "error": str(exc)})
            continue
    
    log_standalone("info", "conditions_poller",
                   f"Processed {records_processed} rows, {records_new} new, {records_duplicate} duplicates",
                   hive_id=str(hive.hive_id))
    
    # Batch insert all new records
    if new_conditions:
        try:
            db.bulk_save_objects(new_conditions)
            db.commit()
            
            log_standalone("info", "conditions_poller",
                           f"💾 Saved {len(new_conditions)} new condition records to database",
                           hive_id=str(hive.hive_id))
        except Exception as exc:
            db.rollback()
            log_standalone("error", "conditions_poller",
                           f"Failed to save condition records: {exc}",
                           hive_id=str(hive.hive_id),
                           details=exc_details(exc))
            raise
    
    return {
        "processed": records_processed,
        "new": records_new,
        "duplicate": records_duplicate
    }
