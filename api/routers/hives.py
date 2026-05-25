from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
import requests

from api.config import settings
from api.database import get_db
from api.models import Alert, Advisory, EnvironmentalData, FarmerDataSource, Hive, User
from api.routers.auth import get_current_user
from sqlalchemy import or_

from api.schemas import (
    AlertResponse,
    DataSourceConfigureHTTPAPI,
    DataSourceConfigureResponse,
    DataSourceResponse,
    HiveCreate,
    HiveCreateResponse,
    HiveDetailResponse,
    HiveResponse,
    HiveUpdate,
    MetricPoint,
)

router = APIRouter(prefix="/hives", tags=["Hives"])


def _safe_hive_folder_name(hive_name: str | None, fallback_hive_id: str) -> str:
    """Return a filesystem-safe hive folder name, falling back to hive_id."""
    candidate = (hive_name or "").strip()
    if not candidate:
        return fallback_hive_id

    # Avoid path traversal/separator issues when users provide custom hive names.
    return candidate.replace("/", "_").replace("\\", "_")


def _create_farmer_hive_folder(api_base_url: str, api_key: str, hive_name: str) -> None:
    """Ask the farmer server to create the hive folder for this hive name."""
    url = f"{api_base_url.rstrip('/')}/recordings/hives/{hive_name}"
    response = requests.post(url, headers={"X-API-Key": api_key}, timeout=15)
    response.raise_for_status()


@router.post("", response_model=HiveCreateResponse, status_code=status.HTTP_201_CREATED)
def create_hive(
    body: HiveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a new hive for the logged-in farmer.

    If the user has server_url and api_key configured, automatically creates
    an HTTP API data source for the hive. Otherwise, creates an inactive
    placeholder that can be configured later.

    Returns suggested_remote_folder — the path where the farmer should store
    recordings on their external server, organized by API key.
    """
    owner_id = (
        body.owner_id
        if (body.owner_id and current_user.role == "admin")
        else current_user.user_id
    )

    hive = Hive(
        owner_id=owner_id,
        hive_location=body.hive_location,
        hive_type=body.hive_type,
        hive_name=body.hive_name,
        installation_date=body.installation_date,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    db.add(hive)
    db.commit()
    db.refresh(hive)

    # Auto-configure HTTP API data source if user has credentials
    if current_user.server_url and current_user.api_key:
        api_config = {
            "api_base_url": current_user.server_url.rstrip("/"),
            "api_key": current_user.api_key,
        }

        # Test connection
        from api.http_connector import test_connection

        connection_test = test_connection(api_config)

        hive_folder = _safe_hive_folder_name(hive.hive_name, str(hive.hive_id))
        _create_farmer_hive_folder(
            current_user.server_url,
            current_user.api_key,
            hive_folder,
        )

        data_source = FarmerDataSource(
            user_id=current_user.user_id,
            hive_id=hive.hive_id,
            source_type="http_api",
            source_path=current_user.server_url,
            connection_config=api_config,
            is_active=connection_test.get(
                "ok", False
            ),  # Only activate if connection succeeds
        )
        db.add(data_source)
        db.commit()

    else:
        # Create inactive placeholder — farmer must configure credentials later
        data_source = FarmerDataSource(
            user_id=current_user.user_id,
            hive_id=hive.hive_id,
            source_type="http_api",
            is_active=False,
        )
        db.add(data_source)
        db.commit()

    # Generate suggested folder path based on user's API key and hive name.
    # The farmer's server organizes recordings by: recordings/<api_key>/<hive_name>/
    # If hive_name is empty, fallback to hive_id.
    suggested_folder = "/home/farmer/recordings"
    if current_user.api_key:
        hive_folder = _safe_hive_folder_name(hive.hive_name, str(hive.hive_id))
        suggested_folder = (
            f"/home/farmer/recordings/{current_user.api_key}/{hive_folder}"
        )

    return HiveCreateResponse(
        hive_id=hive.hive_id,
        owner_id=hive.owner_id,
        hive_name=hive.hive_name,
        hive_location=hive.hive_location,
        hive_type=hive.hive_type,
        installation_date=hive.installation_date,
        current_state=hive.current_state,
        latitude=hive.latitude,
        longitude=hive.longitude,
        suggested_remote_folder=suggested_folder,
    )


@router.put("/{hive_id}", response_model=HiveResponse)
def update_hive(
    hive_id: str,
    body: HiveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a hive. Admin can update any hive; farmers can only update their own."""
    q = db.query(Hive).filter(Hive.hive_id == hive_id)
    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)

    hive = q.first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(hive, field, value)

    db.commit()
    db.refresh(hive)
    return hive


@router.delete("/{hive_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hive(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete a hive (marks as deleted instead of removing from database).
    Admin can delete any hive; farmers can only delete their own.
    """
    q = db.query(Hive).filter(Hive.hive_id == hive_id, Hive.is_deleted == False)
    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)

    hive = q.first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    # Soft delete: mark as deleted instead of removing
    hive.is_deleted = True
    hive.deleted_at = datetime.utcnow()

    # Also deactivate the data source to stop polling
    data_source = (
        db.query(FarmerDataSource).filter(FarmerDataSource.hive_id == hive_id).first()
    )
    if data_source:
        data_source.is_active = False

    db.commit()


@router.get("", response_model=list[HiveResponse])
def list_hives(
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List hives (excludes deleted hives).
    - Admin: all active hives in the system (optionally filtered by ?search=).
    - Farmer: only their own active hives.
    """
    q = db.query(Hive).filter(Hive.is_deleted == False)

    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)

    if search:
        q = q.filter(
            or_(
                Hive.hive_name.ilike(f"%{search}%"),
                Hive.hive_location.ilike(f"%{search}%"),
                Hive.hive_type.ilike(f"%{search}%"),
            )
        )

    return q.order_by(Hive.created_at.desc()).all()


@router.get("/{hive_id}", response_model=HiveDetailResponse)
def get_hive(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return hive detail including latest alert info and recent env metrics.
    Used by the mobile detail screen.
    """
    hive = (
        db.query(Hive)
        .filter(
            Hive.hive_id == hive_id,
            Hive.owner_id == current_user.user_id,
            Hive.is_deleted == False,
        )
        .first()
    )
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    # Latest pending alert for this hive
    latest_alert = (
        db.query(Alert)
        .options(joinedload(Alert.advisory))
        .filter(Alert.hive_id == hive_id)
        .order_by(Alert.alert_timestamp.desc())
        .first()
    )

    alert_title = None
    alert_message = None
    acknowledged = False
    if latest_alert:
        advisory: Advisory | None = latest_alert.advisory
        alert_title = (
            advisory.condition_label
            if advisory and advisory.condition_label
            else latest_alert.recommended_action
        )
        alert_message = (
            advisory.advisory_text
            if advisory and advisory.advisory_text
            else latest_alert.recommended_action
        )
        acknowledged = latest_alert.action_status == "acknowledged"

    # Last 7 environmental readings for the metric chart
    env_rows = (
        db.query(EnvironmentalData)
        .filter(EnvironmentalData.hive_id == hive_id)
        .order_by(EnvironmentalData.recorded_at.desc())
        .limit(7)
        .all()
    )
    metric_series = [
        MetricPoint(
            time_label=r.recorded_at.strftime("%H:%M") if r.recorded_at else "",
            temperature_c=float(r.temperature) if r.temperature is not None else 0.0,
            humidity_percent=float(r.humidity) if r.humidity is not None else 0.0,
        )
        for r in reversed(env_rows)
    ]

    return HiveDetailResponse(
        hive_id=hive.hive_id,
        owner_id=hive.owner_id,
        hive_name=hive.hive_name,
        hive_location=hive.hive_location,
        hive_type=hive.hive_type,
        installation_date=hive.installation_date,
        current_state=hive.current_state,
        latitude=float(hive.latitude) if hive.latitude is not None else None,
        longitude=float(hive.longitude) if hive.longitude is not None else None,
        alert_title=alert_title,
        alert_message=alert_message,
        acknowledged=acknowledged,
        metric_series=metric_series,
    )


@router.post("/{hive_id}/acknowledge", response_model=AlertResponse)
def acknowledge_hive_latest_alert(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Acknowledge the latest pending alert for a hive.
    Called by the mobile app from the hive detail screen.
    """
    hive = (
        db.query(Hive)
        .filter(
            Hive.hive_id == hive_id,
            Hive.owner_id == current_user.user_id,
        )
        .first()
    )
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    alert = (
        db.query(Alert)
        .filter(Alert.hive_id == hive_id, Alert.action_status == "pending")
        .order_by(Alert.alert_timestamp.desc())
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="No pending alert for this hive")

    alert.action_status = "acknowledged"
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/{hive_id}/data-source", response_model=DataSourceResponse)
def get_data_source(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the data source info for a hive."""
    hive = (
        db.query(Hive)
        .filter(
            Hive.hive_id == hive_id,
            Hive.owner_id == current_user.user_id,
        )
        .first()
    )
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    source = (
        db.query(FarmerDataSource).filter(FarmerDataSource.hive_id == hive_id).first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Data source not configured")
    return source


@router.post(
    "/{hive_id}/data-source/configure", response_model=DataSourceConfigureResponse
)
def configure_data_source(
    hive_id: str,
    body: DataSourceConfigureHTTPAPI,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register or update the HTTP API data source for a hive.

    The farmer provides their external server URL and API key. We immediately
    test the connection and return the result.

    Once configured, the background poller will connect every 30 seconds,
    list new audio files via the API, download them, and run inference.

    Example:
        api_base_url: "https://abc123.ngrok-free.dev"
        api_key: "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    """
    hive = (
        db.query(Hive)
        .filter(
            Hive.hive_id == hive_id,
            Hive.owner_id == current_user.user_id,
        )
        .first()
    )
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    api_config = {
        "api_base_url": body.api_base_url.rstrip("/"),
        "api_key": body.api_key,
    }

    from api.http_connector import test_connection

    connection_test = test_connection(api_config)

    source = (
        db.query(FarmerDataSource).filter(FarmerDataSource.hive_id == hive_id).first()
    )

    if source:
        source.source_type = "http_api"
        source.source_path = body.api_base_url
        source.connection_config = api_config
        source.is_active = True
    else:
        source = FarmerDataSource(
            user_id=current_user.user_id,
            hive_id=hive_id,
            source_type="http_api",
            source_path=body.api_base_url,
            connection_config=api_config,
            is_active=True,
        )
        db.add(source)

    db.commit()
    db.refresh(source)

    return DataSourceConfigureResponse(
        source_id=source.source_id,
        hive_id=hive_id,
        source_type="http_api",
        api_base_url=body.api_base_url,
        connection_test=connection_test,
    )
