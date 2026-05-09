"""
Two-phase poller — runs as two independent APScheduler jobs.

Job 1 — scan_all_sources()          (every 30 s)
  Discovers new audio files on the external server (SSH) or a watched
  local folder.  For each new file it creates an AudioSource row with
  status="pending" and stops — no inference here.

Job 2 — process_pending_sources()   (every 30 s, offset by 10 s)
  Picks up every AudioSource row whose status is still "pending",
  fetches the raw audio bytes (via SSH for remote sources, direct
  file-read for local folders / manual uploads), and POSTs them to the
  HuggingFace Inference API through process_audio_file().

This separation means discovery and inference never block each other and
the pending queue is visible in the DB at all times.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from api.config import ROOT
from api.database import SessionLocal
from api.models import AudioSource, FarmerDataSource
from api.processing import process_audio_file
from api.system_logger import exc_details, log_standalone

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


# ---------------------------------------------------------------------------
# Job 1 — Discovery
# ---------------------------------------------------------------------------

def scan_all_sources() -> None:
    """Discover new audio files and register them as pending."""
    db: Session = SessionLocal()
    try:
        sources = (
            db.query(FarmerDataSource)
            .filter(FarmerDataSource.is_active == True)
            .all()
        )
        for source in sources:
            if source.source_type == "folder":
                _scan_folder(source, db)
            elif source.source_type == "ssh":
                _scan_ssh(source, db)
    except Exception as exc:
        log_standalone("error", "poller",
                       f"scan_all_sources failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()


def _known_paths_for_hive(hive_id: int, db: Session) -> set:
    """Return every source_url already registered for this hive, regardless of status.

    Including 'failed' records prevents the discovery job from endlessly
    re-queuing a file that cannot be processed.
    """
    return {
        row.source_url
        for row in db.query(AudioSource.source_url)
        .filter(AudioSource.hive_id == hive_id)
        .all()
    }


def _register_pending(source_url: str, file_format: str, source: FarmerDataSource, db: Session) -> None:
    """Insert an AudioSource row with status='pending'. No inference is triggered here."""
    record = AudioSource(
        hive_id     = source.hive_id,
        source_url  = source_url,
        file_format = file_format,
        status      = "pending",
    )
    db.add(record)
    db.commit()
    log_standalone("info", "poller",
                   f"New {source.source_type} file registered as pending",
                   hive_id=str(source.hive_id),
                   details={"source_url": source_url, "source_type": source.source_type})


def _scan_folder(source: FarmerDataSource, db: Session) -> None:
    """Watch a local folder for new audio files."""
    folder = Path(source.source_path)
    if not folder.exists():
        return

    known = _known_paths_for_hive(source.hive_id, db)

    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS and str(f) not in known:
            _register_pending(str(f), f.suffix.lstrip(".").lower(), source, db)

    source.last_scanned_at = datetime.utcnow()
    db.commit()


def _scan_ssh(source: FarmerDataSource, db: Session) -> None:
    """
    List audio files on the farmer's remote server via SFTP.

    Only the remote path is recorded (as source_url).  The actual audio
    bytes are NOT downloaded here — that happens in process_pending_sources().
    """
    config = source.connection_config
    if not config:
        log_standalone("warning", "ssh",
                       "SSH source has no connection_config — skipping",
                       hive_id=str(source.hive_id))
        return

    import paramiko
    from api.ssh_connector import _build_client

    known = _known_paths_for_hive(source.hive_id, db)
    remote_folder = config.get("remote_folder", "/").rstrip("/")

    try:
        client = _build_client(config)
        sftp = client.open_sftp()
        try:
            remote_files = sftp.listdir_attr(remote_folder)
            for attr in remote_files:
                filename = attr.filename
                if Path(filename).suffix.lower() not in AUDIO_EXTENSIONS:
                    continue
                remote_path = f"{remote_folder}/{filename}"
                if remote_path not in known:
                    fmt = Path(filename).suffix.lstrip(".").lower()
                    _register_pending(remote_path, fmt, source, db)
        finally:
            sftp.close()
            client.close()
    except Exception as exc:
        log_standalone("error", "ssh",
                       f"SSH scan failed: {exc}",
                       hive_id=str(source.hive_id),
                       details=exc_details(exc))

    source.last_scanned_at = datetime.utcnow()
    db.commit()


# ---------------------------------------------------------------------------
# Job 2 — Processing
# ---------------------------------------------------------------------------

def process_pending_sources() -> None:
    """
    Pick up every pending AudioSource, fetch its audio bytes, and send
    them to the HuggingFace Inference API via process_audio_file().
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
                # process_audio_file opens its own session — close ours first
                # to avoid two sessions on the same record
                db.close()
                process_audio_file(record.audio_id, audio_bytes, record.hive_id)
                db = SessionLocal()   # reopen for the next iteration
            except Exception as exc:
                log_standalone("error", "poller",
                               f"Failed to process audio {record.audio_id}: {exc}",
                               hive_id=str(record.hive_id), audio_id=str(record.audio_id),
                               details=exc_details(exc))
    except Exception as exc:
        log_standalone("error", "poller",
                       f"process_pending_sources failed: {exc}",
                       details=exc_details(exc))
    finally:
        db.close()


def _fetch_audio_bytes(record: AudioSource, db: Session) -> bytes:
    """
    Return the raw audio bytes for a pending AudioSource.

    - For SSH sources  : download the file from the remote server on demand.
    - For folder / manual uploads : read directly from the local path stored
      in source_url.
    """
    data_source = (
        db.query(FarmerDataSource)
        .filter(FarmerDataSource.hive_id == record.hive_id)
        .first()
    )

    if data_source and data_source.source_type == "ssh":
        from api.ssh_connector import download_file_bytes
        return download_file_bytes(data_source.connection_config, record.source_url)

    # Local path — folder source or manual upload
    return Path(record.source_url).read_bytes()
