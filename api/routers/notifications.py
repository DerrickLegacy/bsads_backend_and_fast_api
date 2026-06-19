from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import PushNotificationDevice, User
from api.routers.auth import get_current_user
from api.schemas import PushNotificationDeviceRegister, PushNotificationDeviceResponse

router = APIRouter(prefix="/notifications", tags=["Push Notifications"])


@router.post("/register", response_model=PushNotificationDeviceResponse)
def register_push_device(
    device: PushNotificationDeviceRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a push notification device for the current user."""
    # Check if device already exists for this user
    existing_device = db.query(PushNotificationDevice).filter(
        PushNotificationDevice.user_id == current_user.user_id,
        PushNotificationDevice.device_id == device.device_id,
    ).first()

    if existing_device:
        # Update existing device's token and platform
        existing_device.token = device.token
        existing_device.platform = device.platform
        existing_device.is_active = True
        db.commit()
        db.refresh(existing_device)
        return existing_device
    else:
        # Create new device
        new_device = PushNotificationDevice(
            user_id=current_user.user_id,
            token=device.token,
            device_id=device.device_id,
            platform=device.platform,
        )
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        return new_device


@router.get("/devices", response_model=list[PushNotificationDeviceResponse])
def get_user_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all registered push notification devices for the current user."""
    return db.query(PushNotificationDevice).filter(
        PushNotificationDevice.user_id == current_user.user_id
    ).all()
