"""
Audio streaming endpoint - proxies audio files from farmer's servers
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
import httpx
import requests
from urllib.parse import quote

from api.database import get_db
from api.models import AudioSource, FarmerDataSource, Hive, User
from api.routers.auth import get_current_user, _decode_user_from_token

router = APIRouter(prefix="/audio", tags=["Audio"])


@router.get("/{audio_id}/stream")
async def stream_audio(
    audio_id: str,
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Query(default=None, description="JWT token (for media players that can't set headers)"),
):
    """
    Stream an audio file from the farmer's server.
    Accepts auth via Authorization header OR ?token= query param
    (the latter is needed for browser-based media players and expo-av on web).
    """
    # Resolve user from header or query param token
    auth_header = request.headers.get("Authorization", "")
    raw_token = None
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_user = _decode_user_from_token(raw_token, db)
    """
    Stream an audio file from the farmer's server.
    Proxies the file through the backend so the mobile app doesn't need
    direct access to the farmer's ngrok URL.
    """
    audio = db.query(AudioSource).filter(AudioSource.audio_id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    hive = db.query(Hive).filter(Hive.hive_id == audio.hive_id).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    if current_user.role != "admin" and hive.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    data_source = db.query(FarmerDataSource).filter(
        FarmerDataSource.hive_id == audio.hive_id
    ).first()

    if not data_source or not data_source.connection_config:
        raise HTTPException(status_code=404, detail="Data source configuration not found")

    source_url = audio.source_url  # e.g. https://ngrok.../recordings/Hive 03/file.wav

    try:
        from api.http_connector import _translate_localhost_url, _build_session

        api_key = data_source.connection_config.get("api_key", "")
        base_url = data_source.connection_config.get("api_base_url", "").rstrip("/")
        base_url = _translate_localhost_url(base_url)

        # Strategy 1: fetch the file directly from its full source_url
        # (best option — uses the exact URL we stored when the file was registered)
        session = _build_session(api_key, timeout=60)

        # URL-encode the path portion to handle spaces in folder/file names
        from urllib.parse import urlparse, urlunparse, quote as url_quote
        parsed = urlparse(source_url)
        # Re-encode the path (spaces → %20, etc.) without double-encoding slashes
        safe_path = url_quote(parsed.path, safe="/")
        encoded_url = urlunparse(parsed._replace(path=safe_path))

        resp = session.get(encoded_url, timeout=60, stream=True)

        if resp.status_code == 404:
            # Strategy 2: try via the /recordings/{filepath} API endpoint
            # Extract path after /recordings/ and re-request through the API
            if "/recordings/" in source_url:
                filepath = source_url.split("/recordings/", 1)[1]
            else:
                filepath = source_url.split("/")[-1]

            from api.http_connector import download_file_bytes
            audio_bytes = download_file_bytes(
                data_source.connection_config, filepath
            )
            content_type = _content_type(audio.file_format)
            return Response(
                content=audio_bytes,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'inline; filename="{audio.audio_id}.{audio.file_format}"',
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-store",
                },
            )

        resp.raise_for_status()
        audio_bytes = resp.content
        content_type = _content_type(audio.file_format)

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{audio.audio_id}.{audio.file_format}"',
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-store",
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch audio file: {str(exc)}"
        )


def _content_type(file_format: str) -> str:
    return {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
    }.get((file_format or "wav").lower(), "audio/wav")
