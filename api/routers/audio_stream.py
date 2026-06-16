"""
Audio streaming endpoint - proxies audio files from farmer's servers
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import httpx

from api.database import get_db
from api.models import AudioSource, FarmerDataSource, Hive, User
from api.routers.auth import get_current_user

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/{audio_id}/stream")
async def stream_audio(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream an audio file from the farmer's server.
    
    This endpoint acts as a proxy to fetch audio from the farmer's external
    server and stream it to the mobile app. This is necessary because:
    1. The farmer's server may require authentication
    2. Mobile apps can't directly access ngrok URLs with custom headers
    3. Provides a single, consistent API for the mobile app
    """
    # Get the audio source
    audio = db.query(AudioSource).filter(AudioSource.audio_id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Check if user has access to this audio's hive
    hive = db.query(Hive).filter(Hive.hive_id == audio.hive_id).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")
    
    if current_user.role != "admin" and hive.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get the data source configuration for this hive
    data_source = db.query(FarmerDataSource).filter(
        FarmerDataSource.hive_id == audio.hive_id
    ).first()
    
    if not data_source or not data_source.connection_config:
        raise HTTPException(
            status_code=404,
            detail="Data source configuration not found"
        )
    
    # Extract the file path from the source_url
    # Format: https://server.ngrok.dev/recordings/Hive 02/file.wav
    # We need: /recordings/Hive 02/file.wav or just the filename
    source_url = audio.source_url
    
    try:
        # If source_url contains "/recordings/", extract the path after it
        if "/recordings/" in source_url:
            filepath = source_url.split("/recordings/", 1)[1]
        else:
            # Fallback: use the full URL
            filepath = source_url.split("/")[-1]
        
        # Use http_connector to download the file
        from api.http_connector import download_file_bytes
        
        audio_bytes = download_file_bytes(data_source.connection_config, filepath)
        
        # Determine content type
        content_type_map = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "flac": "audio/flac",
        }
        content_type = content_type_map.get(audio.file_format.lower(), "audio/wav")
        
        # Return as streaming response
        return StreamingResponse(
            iter([audio_bytes]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{audio.audio_id}.{audio.file_format}"',
                "Accept-Ranges": "bytes",
            }
        )
    
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch audio file: {str(exc)}"
        )
