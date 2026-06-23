from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
import requests

from api.config import settings
from api.database import get_db
from api.models import Alert, Advisory, EnvironmentalData, FarmerDataSource, Hive, InferenceResult, User
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


@router.post("", response_model=HiveCreateResponse, status_code=status.HTTP_201_CREATED)
def create_hive(
    body: HiveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a new hive for the logged-in farmer.

    If the user has server_url and api_key configured, automatically creates
    an HTTP API data source for the hive and marks it as ACTIVE by default.
    The poller will handle connection errors gracefully and log them.

    If the user has no credentials, creates an inactive placeholder that must
    be configured later via the /data-source/configure endpoint.

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
    folder_created = False
    folder_creation_error = None
    
    if current_user.server_url and current_user.api_key:
        api_config = {
            "api_base_url": current_user.server_url.rstrip("/"),
            "api_key": current_user.api_key,
        }

        # Test connection
        from api.http_connector import test_connection

        connection_test = test_connection(api_config)

        # Try to create the hive folder on the farmer's server
        # NOTE: This is optional - the farmer's server may auto-create folders
        # or the farmer may manually create them. We try but don't fail if it doesn't work.
        hive_folder = _safe_hive_folder_name(hive.hive_name, str(hive.hive_id))
        
        from api.http_connector import create_hive_folder as http_create_hive_folder
        folder_result = http_create_hive_folder(api_config, hive_folder)
        
        if folder_result.get("ok"):
            folder_created = True
        else:
            # This is expected if the farmer's server doesn't support folder creation endpoint
            # The folder will be created when the farmer first uploads audio files
            folder_creation_error = folder_result.get("error", "Folder auto-creation not supported")
            from api.models import SystemLog
            import logging
            logger = logging.getLogger("bsads")
            logger.info(f"Hive folder creation skipped: {hive_folder} - {folder_creation_error}")
            db.add(SystemLog(
                level="info",
                event_type="http_api",
                message=f"Hive folder not auto-created: {hive_folder}",
                details={
                    "hive_id": str(hive.hive_id),
                    "suggested_folder": hive_folder,
                    "reason": folder_creation_error
                },
                hive_id=hive.hive_id,
                user_id=current_user.user_id,
            ))
            db.commit()

        data_source = FarmerDataSource(
            user_id=current_user.user_id,
            hive_id=hive.hive_id,
            source_type="http_api",
            source_path=current_user.server_url,
            connection_config=api_config,
            is_active=True,  # Always active - poller will handle connection errors gracefully
        )
        db.add(data_source)
        db.commit()

    else:
        # Create inactive placeholder — farmer must configure credentials later
        # This remains inactive until credentials are provided
        data_source = FarmerDataSource(
            user_id=current_user.user_id,
            hive_id=hive.hive_id,
            source_type="http_api",
            is_active=False,  # Inactive until credentials are configured
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
        folder_created=folder_created,
        folder_creation_error=folder_creation_error,
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
    
    Returns last_inference_at: timestamp of the most recent inference for each hive.
    """
    from sqlalchemy import func
    from api.models import InferenceResult
    
    # Subquery to get the latest inference timestamp for each hive
    latest_inference_subq = (
        db.query(
            InferenceResult.hive_id,
            func.max(InferenceResult.analyzed_at).label('last_inference_at')
        )
        .group_by(InferenceResult.hive_id)
        .subquery()
    )
    
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

    # Left join with the latest inference subquery
    q = q.outerjoin(latest_inference_subq, Hive.hive_id == latest_inference_subq.c.hive_id)
    
    hives = q.order_by(Hive.created_at.desc()).all()
    
    # Build response with last_inference_at
    result = []
    for hive in hives:
        # Get the last inference timestamp for this hive
        last_inference = (
            db.query(InferenceResult.analyzed_at)
            .filter(InferenceResult.hive_id == hive.hive_id)
            .order_by(InferenceResult.analyzed_at.desc())
            .first()
        )
        
        hive_dict = {
            "hive_id": hive.hive_id,
            "owner_id": hive.owner_id,
            "hive_name": hive.hive_name,
            "hive_location": hive.hive_location,
            "hive_type": hive.hive_type,
            "installation_date": hive.installation_date,
            "current_state": hive.current_state,
            "latitude": float(hive.latitude) if hive.latitude is not None else None,
            "longitude": float(hive.longitude) if hive.longitude is not None else None,
            "last_inference_at": last_inference[0] if last_inference else None
        }
        result.append(hive_dict)
    
    return result


@router.get("/{hive_id}", response_model=HiveDetailResponse)
def get_hive(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return hive detail including latest alert info, recent env metrics, and weather data.
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
        .filter(Alert.hive_id == hive_id)
        .order_by(Alert.alert_timestamp.desc())
        .first()
    )

    alert_title = None
    alert_message = None
    acknowledged = False
    confidence_score = None
    last_analysis_time = None
    prediction_details = None
    
    # Get the latest inference for this hive regardless of alert
    latest_inference = (
        db.query(InferenceResult)
        .filter(InferenceResult.hive_id == hive_id)
        .order_by(InferenceResult.analyzed_at.desc())
        .first()
    )
    if latest_inference:
        confidence_score = float(latest_inference.confidence_score) if latest_inference.confidence_score is not None else None
        if latest_inference.analyzed_at:
            last_analysis_time = latest_inference.analyzed_at.isoformat()
        prediction_details = latest_inference.prediction_details  # Already a dict (JSONB)
    
    if latest_alert:
        # Alert model doesn't have advisory relationship - use recommended_action directly
        alert_title = latest_alert.recommended_action or "Alert"
        alert_message = latest_alert.recommended_action or "No details available"
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

    # Fetch current weather if coordinates are available
    weather_data = None
    if hive.latitude is not None and hive.longitude is not None:
        from api.weather_service import fetch_weather, get_weather_description
        weather = fetch_weather(float(hive.latitude), float(hive.longitude))
        if weather:
            weather_data = {
                "temperature": weather.temperature,
                "humidity": weather.humidity,
                "timestamp": weather.timestamp,
                "weather_description": get_weather_description(weather.weather_code)
            }

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
        last_inference_at=latest_inference.analyzed_at if latest_inference else None,
        alert_title=alert_title,
        alert_message=alert_message,
        acknowledged=acknowledged,
        confidence_score=confidence_score,
        prediction_details=prediction_details,
        metric_series=metric_series,
        weather=weather_data,
        last_analysis_time=last_analysis_time,
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


@router.post("/{hive_id}/data-source/activate")
def activate_data_source(
    hive_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually activate a data source without testing the connection.
    
    Use this when you know your server is configured correctly but the
    connection test failed for temporary reasons (firewall, network issues, etc.)
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
    
    source = (
        db.query(FarmerDataSource).filter(FarmerDataSource.hive_id == hive_id).first()
    )
    
    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    if not source.connection_config:
        raise HTTPException(
            status_code=400,
            detail="Data source has no connection configuration. Please configure it first."
        )
    
    source.is_active = True
    db.commit()
    
    return {
        "detail": "Data source activated successfully",
        "source_id": source.source_id,
        "hive_id": hive_id,
        "is_active": True
    }


@router.get("/{hive_id}/conditions")
def get_hive_conditions(
    hive_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return recent internal hive sensor readings (temp + humidity from the
    3 hive zones: honey, brood, exterior) for display in the mobile app.
    Ordered oldest-first so the frontend can draw a time-series chart.
    """
    from api.models import HiveCondition

    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
        Hive.is_deleted == False,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    rows = (
        db.query(HiveCondition)
        .filter(HiveCondition.hive_id == hive_id)
        .order_by(HiveCondition.recorded_at.desc())
        .limit(limit)
        .all()
    )
    # Return oldest-first for charting
    rows = list(reversed(rows))

    return [
        {
            "time_label": r.recorded_at.strftime("%H:%M") if r.recorded_at else "",
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else "",
            "temp_honey": float(r.temp_honey) if r.temp_honey is not None else None,
            "temp_brood": float(r.temp_brood) if r.temp_brood is not None else None,
            "temp_exterior": float(r.temp_exterior) if r.temp_exterior is not None else None,
            "humidity_honey": float(r.humidity_honey) if r.humidity_honey is not None else None,
            "humidity_brood": float(r.humidity_brood) if r.humidity_brood is not None else None,
            "humidity_exterior": float(r.humidity_exterior) if r.humidity_exterior is not None else None,
        }
        for r in rows
    ]


@router.get("/{hive_id}/state-trend")
def get_hive_state_trend(
    hive_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the last N inference results for a hive as time-series data
    suitable for the hive state trend line chart on the mobile detail screen.
    Each point has a time label and the classified hive_state.
    """
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
        Hive.is_deleted == False,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    results = (
        db.query(InferenceResult)
        .filter(InferenceResult.hive_id == hive_id)
        .order_by(InferenceResult.analyzed_at.desc())
        .limit(limit)
        .all()
    )
    results = list(reversed(results))

    return [
        {
            "time_label": r.analyzed_at.strftime("%H:%M") if r.analyzed_at else "",
            "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else "",
            "hive_state": r.hive_state,
            "confidence": float(r.confidence_score) if r.confidence_score is not None else 0,
        }
        for r in results
    ]
