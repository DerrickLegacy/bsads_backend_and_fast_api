"""
IoT Device Integration - Webhook/Callback Endpoints (Optional)

NOTE: The primary device integration flow is:
Device → Simulation Server (direct upload) → Backend polls periodically

These endpoints are optional and can be used for:
1. Real-time notifications when device uploads complete
2. Trigger immediate processing instead of waiting for poll cycle
3. Direct uploads if simulation server is unavailable (fallback)

For normal operation, devices should upload directly to the simulation server:
- Audio: POST {server_url}/recordings/hives/{hive_name}/upload
- CSV: POST {server_url}/conditions/hives/{hive_name}/upload

The backend will automatically discover and process files via the polling mechanism.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.database import get_db
from api.models import User

router = APIRouter(prefix="/device", tags=["Device Integration"])


# ---------------------------------------------------------------------------
# Authentication Helper
# ---------------------------------------------------------------------------
def _require_device_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> User:
    """Validate device API key and return the user (farmer)."""
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return user


# ---------------------------------------------------------------------------
# Optional: Webhook/Notification Endpoint
# ---------------------------------------------------------------------------
class UploadNotification(BaseModel):
    hive_name: str
    file_type: str  # "audio" or "conditions"
    filename: str
    uploaded_at: str


@router.post("/notify/upload")
async def notify_upload_complete(
    notification: UploadNotification,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_device_api_key),
):
    """
    Optional webhook endpoint for devices to notify when upload completes.
    
    This can trigger immediate processing instead of waiting for the poll cycle.
    However, the polling mechanism handles everything automatically, so this
    endpoint is not required for normal operation.
    """
    # Log the notification
    # Could trigger immediate processing here if needed
    
    return {
        "status": "acknowledged",
        "message": "Upload notification received. File will be processed in the next poll cycle."
    }


# ---------------------------------------------------------------------------
# Status/Health Check
# ---------------------------------------------------------------------------
@router.get("/status")
async def device_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_device_api_key),
):
    """
    Health check endpoint for devices to verify connectivity and credentials.
    """
    return {
        "status": "ok",
        "user_id": current_user.user_id,
        "email": current_user.email,
        "server_url": current_user.server_url,
        "has_api_key": current_user.api_key is not None
    }
