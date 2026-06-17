"""
Concurrent version of the poller with improved scalability.

This version processes multiple hives and audio files concurrently,
dramatically improving throughput at scale.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import AudioSource, FarmerDataSource, Hive
from api.processing import process_audio_file
from api.system_logger import exc_details, log_standalone

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}

# Concurrency settings - tune based on your infrastructure
MAX_DISCOVERY_WORKERS = 5   # Reduced from 10 to avoid overwhelming unreachable APIs
MAX_INFERENCE_WORKERS = 5   # Concurrent inference API calls
BATCH_SIZE = 50             # Process audio files in batches


# ---------------------------------------------------------------------------
# Job 1 — Discovery (Concurrent)
# ---------------------------------------------------------------------------

def scan_all_sources_concurrent() -> None:
    """
    Discover new audio files on all active data sources concurrently.
    
    Processes up to MAX_DISCOVERY_WORKERS sources in parallel,
    dramatically improving throughput for large deployments.
    """
    db: Session = SessionLocal()
    try:
        sources = (
            db.query(FarmerDataSource)
            .filter(FarmerDataSource.is_active == True)
            .all()
        )
        
        if not sources:
            log_standalone("info", "poller",
                           "No active data sources to scan")
            return
        
        log_standalone("info", "poller",
                       f"🔍 Discovery poller: scanning {len(sources)} active data sources (concurrent)")
        
        # Process sources concurrently
        with ThreadPoolExecutor(max_workers=MAX_DISCOVERY_WORKERS) as executor:
            # Submit all tasks
            future_to_source = {
                executor.submit(_scan_one_source_safe, source): source
                for source in sources
            }
            
            # Collect results
            success_count = 0
            error_count = 0
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    result = future.result()
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as exc:
                    error_count += 1
                    log_standalone("error", "poller",
                                   f"Unexpected error scanning source {source.source_id}: {exc}",
                                   hive_id=str(source.hive_id),
                                   details=exc_details(exc))
        
        log_standalone("info", "poller",
                       f"✓ Discovery poller: completed scan ({success_count} success, {error_count} errors)")
    
    except Exception as exc:
        log_standalone("error", "poller",
                       f"scan_all_sources_concurrent failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()


def _scan_one_source_safe(source: FarmerDataSource) -> bool:
    """
    Scan a single source with its own DB session.
    Returns True on success, False on error.
    """
    db: Session = SessionLocal()
    try:
        # Check if source has recent failures - skip temporarily if it's repeatedly failing
        if source.last_error_at:
            # Skip sources that failed in the last 10 minutes to avoid wasting resources
            time_since_error = datetime.utcnow() - source.last_error_at
            if time_since_error < timedelta(minutes=10):
                log_standalone("info", "poller",
                               f"Skipping source that recently failed (will retry after 10 min cooldown)",
                               hive_id=str(source.hive_id),
                               details={"last_error": source.last_error_at.isoformat()})
                return False
        
        if source.source_type == "http_api":
            _scan_http_api(source, db)
            # Clear error timestamp on success
            source.last_error_at = None
            db.commit()
            return True
        else:
            log_standalone("warning", "poller",
                           f"Unsupported source type: {source.source_type}",
                           hive_id=str(source.hive_id))
            return False
    except Exception as exc:
        log_standalone("error", "http_api",
                       f"❌ Failed to scan source for hive {source.hive_id}: {exc}",
                       hive_id=str(source.hive_id),
                       details=exc_details(exc))
        
        # Record error timestamp for circuit breaker
        source.last_error_at = datetime.utcnow()
        db.commit()
        return False
    finally:
        db.close()


def _scan_http_api(source: FarmerDataSource, db: Session) -> None:
    """
    List audio files from the farmer's HTTP API server for a specific hive
    and register any that have not been seen before.
    """
    config = source.connection_config
    if not config:
        log_standalone("warning", "http_api",
                       "HTTP API source has no connection_config — skipping",
                       hive_id=str(source.hive_id))
        return

    from api.http_connector import list_recordings, get_recording_url

    # Get the hive name
    hive_record = db.query(Hive).filter(Hive.hive_id == source.hive_id).first()
    
    if not hive_record or not hive_record.hive_name:
        log_standalone("warning", "http_api",
                       f"Hive has no name, cannot scan recordings",
                       hive_id=str(source.hive_id))
        return
    
    hive_name = hive_record.hive_name
    
    # Get known paths for this hive
    known = {
        row.source_url
        for row in db.query(AudioSource.source_url)
        .filter(AudioSource.hive_id == source.hive_id)
        .all()
    }

    try:
        log_standalone("info", "http_api",
                       f"📡 Listing recordings for hive '{hive_name}' ({source.hive_id})",
                       hive_id=str(source.hive_id))
        
        # List recordings for this specific hive using hive_name
        filepaths = list_recordings(config, hive_name=hive_name)
        
        log_standalone("info", "http_api",
                       f"Found {len(filepaths)} files on remote server",
                       hive_id=str(source.hive_id),
                       details={"files": filepaths[:5]})
        
        new_count = 0
        for filepath in filepaths:
            if Path(filepath).suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            
            recording_url = get_recording_url(config, filepath)
            
            if recording_url not in known:
                fmt = Path(filepath).suffix.lstrip(".").lower()
                _register_pending(recording_url, fmt, source, db)
                new_count += 1
        
        if new_count > 0:
            log_standalone("info", "http_api",
                           f"✓ Registered {new_count} new audio files",
                           hive_id=str(source.hive_id))
        else:
            log_standalone("info", "http_api",
                           f"No new files (all {len(filepaths)} already known)",
                           hive_id=str(source.hive_id))
    
    except Exception as exc:
        log_standalone("error", "http_api",
                       f"❌ HTTP API scan failed: {exc}",
                       hive_id=str(source.hive_id),
                       details=exc_details(exc))

    source.last_scanned_at = datetime.utcnow()
    db.commit()


def _register_pending(source_url: str, file_format: str, source: FarmerDataSource, db: Session) -> None:
    """
    Insert an AudioSource row with status='pending' and record environmental data.
    Environmental data is recorded at audio capture time for accurate correlation.
    """
    from api.models import EnvironmentalData, Hive
    from api.weather_service import fetch_weather
    
    record = AudioSource(
        hive_id     = source.hive_id,
        source_url  = source_url,
        file_format = file_format,
        status      = "pending",
    )
    db.add(record)
    db.commit()
    
    log_standalone("info", "poller",
                   "New audio file registered as pending",
                   hive_id=str(source.hive_id),
                   details={"source_url": source_url})
    
    # Record environmental data at the exact time of audio capture
    try:
        hive = db.query(Hive).filter(Hive.hive_id == source.hive_id).first()
        
        if not hive:
            log_standalone("warning", "environmental_data",
                           "Cannot record environmental data: hive not found",
                           hive_id=str(source.hive_id))
            return
        
        # Check if hive has coordinates
        if not hive.latitude or not hive.longitude:
            log_standalone("warning", "environmental_data",
                           f"Cannot record environmental data: hive has no coordinates",
                           hive_id=str(source.hive_id))
            return
        
        # Fetch weather data
        weather = fetch_weather(float(hive.latitude), float(hive.longitude))
        
        if not weather:
            log_standalone("warning", "environmental_data",
                           "Weather service unavailable, skipping environmental data recording",
                           hive_id=str(source.hive_id))
            return
        
        # Create environmental data record
        env_data = EnvironmentalData(
            hive_id=source.hive_id,
            temperature=weather.temperature,
            humidity=weather.humidity,
        )
        
        db.add(env_data)
        db.commit()
        
        log_standalone("info", "environmental_data",
                       f"Recorded environmental data: temp={weather.temperature}°C, humidity={weather.humidity}%",
                       hive_id=str(source.hive_id),
                       details={
                           "temperature": weather.temperature,
                           "humidity": weather.humidity,
                           "timestamp": weather.timestamp,
                           "audio_source": source_url
                       })
    
    except Exception as exc:
        # Don't fail audio registration if weather recording fails
        log_standalone("error", "environmental_data",
                       f"Failed to record environmental data: {exc}",
                       hive_id=str(source.hive_id),
                       details=exc_details(exc))


# ---------------------------------------------------------------------------
# Job 2 — Processing (Concurrent with Batching)
# ---------------------------------------------------------------------------

def process_pending_sources_concurrent() -> None:
    """
    Process pending audio files in batches with concurrent execution.
    
    Processes up to MAX_INFERENCE_WORKERS files in parallel per batch,
    with controlled memory usage through batching.
    """
    db: Session = SessionLocal()
    try:
        # Count total pending
        total_pending = (
            db.query(AudioSource)
            .filter(AudioSource.status == "pending")
            .count()
        )
        
        if total_pending == 0:
            log_standalone("info", "poller",
                           "⏭️  Inference poller: no pending audio sources")
            return
        
        log_standalone("info", "poller",
                       f"🎵 Inference poller: processing {total_pending} pending audio sources (batched)")
        
        processed_count = 0
        error_count = 0
        
        # Process in batches
        while True:
            # Fetch next batch
            batch = (
                db.query(AudioSource)
                .filter(AudioSource.status == "pending")
                .limit(BATCH_SIZE)
                .all()
            )
            
            if not batch:
                break
            
            # Process batch concurrently
            with ThreadPoolExecutor(max_workers=MAX_INFERENCE_WORKERS) as executor:
                future_to_record = {
                    executor.submit(_process_one_audio_safe, record): record
                    for record in batch
                }
                
                for future in as_completed(future_to_record):
                    record = future_to_record[future]
                    try:
                        result = future.result()
                        if result:
                            processed_count += 1
                        else:
                            error_count += 1
                    except Exception as exc:
                        error_count += 1
                        log_standalone("error", "poller",
                                       f"Unexpected error processing audio {record.audio_id}: {exc}",
                                       hive_id=str(record.hive_id),
                                       audio_id=str(record.audio_id),
                                       details=exc_details(exc))
            
            # Refresh session for next batch
            db.close()
            db = SessionLocal()
        
        log_standalone("info", "poller",
                       f"✓ Inference poller: completed ({processed_count} success, {error_count} errors)")
    
    except Exception as exc:
        log_standalone("error", "poller",
                       f"process_pending_sources_concurrent failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()


def _process_one_audio_safe(record: AudioSource) -> bool:
    """
    Process a single audio file with its own DB session.
    Returns True on success, False on error.
    """
    db: Session = SessionLocal()
    try:
        # Fetch audio bytes
        audio_bytes = _fetch_audio_bytes(record, db)
        
        # Close DB before long-running inference call
        db.close()
        
        # Run inference (this is the slow part - 30+ seconds)
        process_audio_file(record.audio_id, audio_bytes, record.hive_id)
        
        return True
    
    except Exception as exc:
        log_standalone("error", "poller",
                       f"Failed to fetch/process audio {record.audio_id}: {exc}",
                       hive_id=str(record.hive_id),
                       audio_id=str(record.audio_id),
                       details=exc_details(exc))
        return False
    finally:
        db.close()


def _fetch_audio_bytes(record: AudioSource, db: Session) -> bytes:
    """Download the audio file from the farmer's data source (HTTP API only)."""
    data_source = (
        db.query(FarmerDataSource)
        .filter(FarmerDataSource.hive_id == record.hive_id)
        .first()
    )
    if not data_source or not data_source.connection_config:
        raise ValueError(f"No connection config found for hive {record.hive_id}")

    if data_source.source_type == "http_api":
        from api.http_connector import download_file_bytes as http_download
        
        if "/recordings/" in record.source_url:
            filepath = record.source_url.split("/recordings/", 1)[1]
        else:
            raise ValueError(f"Invalid source_url format: {record.source_url}")
        
        return http_download(data_source.connection_config, filepath)
    else:
        raise ValueError(f"Unsupported source type: {data_source.source_type}")


# ---------------------------------------------------------------------------
# Job 3 — Recovery (Clean up stuck records)
# ---------------------------------------------------------------------------

def recover_stuck_records() -> None:
    """
    Reset 'processing' records that have been stuck for more than 10 minutes.
    
    This handles cases where the server crashed or was restarted while
    processing audio files.
    """
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        
        stuck = (
            db.query(AudioSource)
            .filter(
                AudioSource.status == "processing",
                AudioSource.ingestion_timestamp < cutoff
            )
            .all()
        )
        
        if not stuck:
            return
        
        log_standalone("warning", "poller",
                       f"🔧 Found {len(stuck)} stuck 'processing' records, resetting to 'pending'")
        
        for record in stuck:
            record.status = "pending"
            log_standalone("warning", "poller",
                          f"Reset stuck record {record.audio_id}",
                          hive_id=str(record.hive_id),
                          audio_id=str(record.audio_id))
        
        db.commit()
        
        log_standalone("info", "poller",
                       f"✓ Reset {len(stuck)} stuck records")
    
    except Exception as exc:
        log_standalone("error", "poller",
                       f"recover_stuck_records failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()
