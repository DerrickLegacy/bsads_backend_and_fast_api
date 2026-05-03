"""
Folder-watch and SSH poller.

Runs every 30 seconds (via APScheduler). Supports two source types:

  'folder' — watches a local folder that the farmer (or their device) drops
             audio files into.  Path: data_sources/{user_id}/{hive_id}/

  'ssh'    — connects to the farmer's remote server via SFTP, downloads any
             new audio files to a local staging area, then runs inference.
             Credentials stored in FarmerDataSource.connection_config (JSON).

Both paths funnel into process_audio_file() so inference, alert generation,
and DB writes are identical regardless of how the audio arrived.
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from api.config import ROOT
from api.database import SessionLocal
from api.models import AudioSource, FarmerDataSource
from api.processing import process_audio_file

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}


def scan_all_sources() -> None:
    """Entry point called by APScheduler every 30 seconds."""
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
        print(f"[POLLER] scan error: {exc}")
    finally:
        db.close()


def _known_paths_for_hive(hive_id: int, db: Session) -> set:
    """Return set of source_url strings already registered for this hive."""
    return {
        row.source_url
        for row in db.query(AudioSource.source_url)
        .filter(
            AudioSource.hive_id == hive_id,
            AudioSource.status != "failed",
        )
        .all()
    }


def _register_and_process(audio_file: Path, source_url: str, source: FarmerDataSource, db: Session) -> None:
    """Create an AudioSource record and kick off inference."""
    record = AudioSource(
        hive_id     = source.hive_id,
        source_url  = source_url,
        file_format = audio_file.suffix.lstrip(".").lower(),
        status      = "pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    print(f"[POLLER/{source.source_type}] hive={source.hive_id} → {audio_file.name}")
    process_audio_file(record.audio_id, audio_file, source.hive_id)


def _scan_folder(source: FarmerDataSource, db: Session) -> None:
    folder = Path(source.source_path)
    if not folder.exists():
        return

    known = _known_paths_for_hive(source.hive_id, db)

    new_files = [
        f for f in folder.iterdir()
        if f.is_file()
        and f.suffix.lower() in AUDIO_EXTENSIONS
        and str(f) not in known
    ]

    for audio_file in new_files:
        _register_and_process(audio_file, str(audio_file), source, db)

    source.last_scanned_at = datetime.utcnow()
    db.commit()


def _scan_ssh(source: FarmerDataSource, db: Session) -> None:
    """
    Download new audio files from the farmer's remote server via SFTP,
    then run inference on each one.

    Downloaded files are staged at:  downloads/{user_id}/{hive_id}/

    source_url stored in audio_sources = the *remote* path, so we can
    track which remote files we've already processed even after a restart.
    """
    config = source.connection_config
    if not config:
        print(f"[POLLER/ssh] hive={source.hive_id}: no connection_config — skipping")
        return

    from api.ssh_connector import download_new_files

    staging_dir = ROOT / "downloads" / str(source.user_id) / str(source.hive_id)
    known = _known_paths_for_hive(source.hive_id, db)

    try:
        local_files = download_new_files(config, known, staging_dir)
    except Exception as exc:
        print(f"[POLLER/ssh] hive={source.hive_id}: SSH error — {exc}")
        source.last_scanned_at = datetime.utcnow()
        db.commit()
        return

    remote_folder = config.get("remote_folder", "").rstrip("/")
    for local_path in local_files:
        remote_path = f"{remote_folder}/{local_path.name}"
        _register_and_process(local_path, remote_path, source, db)

    source.last_scanned_at = datetime.utcnow()
    db.commit()
