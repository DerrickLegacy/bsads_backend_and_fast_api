"""
Two-phase poller — runs as two independent APScheduler jobs.

Job 1 — scan_all_sources()          (every 30 s)
  Connects to each farmer's data source (HTTP API), lists new audio files,
  and registers each as a pending AudioSource row.

Job 2 — process_pending_sources()   (every 30 s, offset by 10 s)
  Picks up every pending AudioSource, downloads the audio bytes via HTTP API,
  and sends them to the HuggingFace Inference API through process_audio_file().

Supported source types:
  - http_api: HTTP REST API with API key authentication
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import AudioSource, FarmerDataSource
from api.processing import process_audio_file
from api.system_logger import exc_details, log_standalone

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


# ---------------------------------------------------------------------------
# Job 1 — Discovery
# ---------------------------------------------------------------------------

def scan_all_sources() -> None:
    """Discover new audio files on all active data sources and register as pending."""
    db: Session = SessionLocal()
    try:
        sources = (
            db.query(FarmerDataSource)
            .filter(FarmerDataSource.is_active == True)
            .all()
        )
        for source in sources:
            if source.source_type == "http_api":
                try:
                    _scan_http_api(source, db)
                except Exception as exc:
                    # Log error but continue with other sources
                    log_standalone("error", "http_api",
                                   f"❌ Failed to scan source for hive {source.hive_id}: {exc}",
                                   hive_id=str(source.hive_id),
                                   details=exc_details(exc))
            else:
                log_standalone("warning", "poller",
                               f"Unsupported source type: {source.source_type}. Only http_api is supported.",
                               hive_id=str(source.hive_id))
    except Exception as exc:
        log_standalone("error", "poller",
                       f"scan_all_sources failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()


def _known_paths_for_hive(hive_id: str, db: Session) -> set:
    """
    Return every source_url already registered for this hive.
    Including 'failed' records prevents endlessly re-queuing a broken file.
    """
    return {
        row.source_url
        for row in db.query(AudioSource.source_url)
        .filter(AudioSource.hive_id == hive_id)
        .all()
    }


def _register_pending(source_url: str, file_format: str, source: FarmerDataSource, db: Session) -> None:
    """Insert an AudioSource row with status='pending'."""
    record = AudioSource(
        hive_id=source.hive_id,
        source_url=source_url,
        file_format=file_format,
        status="pending",
    )
    db.add(record)
    db.commit()
    log_standalone("info", "poller",
                   "New audio file registered as pending",
                   hive_id=str(source.hive_id),
                   details={"source_url": source_url})


def _scan_http_api(source: FarmerDataSource, db: Session) -> None:
    """
    List audio files from the farmer's HTTP API server for a specific hive
    and register any that have not been seen before.

    Files are organized by hive: recordings/<api_key>/<hive_id>/<filename>
    """
    config = source.connection_config
    if not config:
        log_standalone("warning", "http_api",
                       "HTTP API source has no connection_config — skipping",
                       hive_id=str(source.hive_id))
        return

    from api.http_connector import list_recordings, get_recording_url

    known = _known_paths_for_hive(source.hive_id, db)

    try:
        # List recordings for this specific hive
        filepaths = list_recordings(config, hive_id=str(source.hive_id))

        for filepath in filepaths:
            # filepath format: "Hive 22/filename.wav"
            if Path(filepath).suffix.lower() not in AUDIO_EXTENSIONS:
                continue

            # Use full URL as the canonical identifier (matches source_url)
            recording_url = get_recording_url(config, filepath)

            if recording_url not in known:
                fmt = Path(filepath).suffix.lstrip(".").lower()
                _register_pending(recording_url, fmt, source, db)

    except Exception as exc:
        log_standalone("error", "http_api",
                       f"❌ HTTP API scan failed: {exc}",
                       hive_id=str(source.hive_id),
                       details=exc_details(exc))

    source.last_scanned_at = datetime.utcnow()
    db.commit()


# ---------------------------------------------------------------------------
# Job 2 — Processing
# ---------------------------------------------------------------------------

def process_pending_sources() -> None:
    """
    Pick up every pending AudioSource, fetch bytes via HTTP API, and run inference.
    """
    db: Session = SessionLocal()
    try:
        pending = (
            db.query(AudioSource)
            .filter(AudioSource.status == "pending")
            .all()
        )
        for record in pending:
            try:
                audio_bytes = _fetch_audio_bytes(record, db)
                db.close()
                process_audio_file(
                    record.audio_id, audio_bytes, record.hive_id)
                db = SessionLocal()
            except Exception as exc:
                log_standalone("error", "poller",
                               f"Failed to fetch/process audio {record.audio_id}: {exc}",
                               hive_id=str(record.hive_id),
                               audio_id=str(record.audio_id),
                               details=exc_details(exc))
    except Exception as exc:
        log_standalone("error", "poller",
                       f"process_pending_sources failed: {exc}",
                       details=exc_details(exc))
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
        raise ValueError(
            f"No connection config found for hive {record.hive_id}")

    if data_source.source_type == "http_api":
        from api.http_connector import download_file_bytes as http_download
        # Extract filepath from URL (e.g., "https://server.com/recordings/hive-id/file.wav" -> "hive-id/file.wav")
        # URL format: https://server.com/recordings/hive-id/filename.wav
        filepath = "/".join(record.source_url.split("/recordings/")
                            [1].split("/"))
        return http_download(data_source.connection_config, filepath)
    else:
        raise ValueError(
            f"Unsupported source type: {data_source.source_type}. Only http_api is supported.")
