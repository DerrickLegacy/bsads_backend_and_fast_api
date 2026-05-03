"""
Manual audio upload endpoint.

POST /audio/upload
  Farmer uploads a .wav file directly (alternative to using the watched folder).
  Returns HTTP 202 immediately; inference runs in a background task.
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.config import ROOT, settings
from api.database import get_db
from api.models import AudioSource, Hive, User
from api.processing import process_audio_file
from api.routers.auth import get_current_user
from api.schemas import AudioUploadResponse

router = APIRouter(prefix="/audio", tags=["Audio"])

UPLOAD_ROOT = ROOT / settings.upload_dir


@router.post("/upload", response_model=AudioUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="WAV audio recording from the hive"),
    hive_id: int = Form(..., description="ID of the hive this recording belongs to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a hive audio recording for inference.

    Returns immediately (HTTP 202 Accepted). Inference runs in the
    background — poll GET /hives/{hive_id}/inferences/latest for the result.

    Alternative: drop the file into the watched folder at
    data_sources/{user_id}/{hive_id}/ and the poller will pick it up.
    """
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.user_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found or does not belong to you")

    if Path(file.filename).suffix.lower() not in {".wav", ".mp3", ".flac"}:
        raise HTTPException(status_code=400, detail="Only WAV, MP3, or FLAC files are accepted")

    # Save to uploads/{user_id}/{hive_id}/filename
    save_dir = UPLOAD_ROOT / str(current_user.user_id) / str(hive_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / file.filename

    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Register in audio_sources
    audio_record = AudioSource(
        hive_id     = hive_id,
        source_url  = str(save_path),
        file_format = Path(file.filename).suffix.lstrip(".").lower(),
        status      = "pending",
    )
    db.add(audio_record)
    db.commit()
    db.refresh(audio_record)

    # Queue background inference
    background_tasks.add_task(
        process_audio_file,
        audio_record.audio_id,
        save_path,
        hive_id,
    )

    return AudioUploadResponse(
        audio_id = audio_record.audio_id,
        hive_id  = hive_id,
        message  = "File received. Inference is running in the background.",
    )
