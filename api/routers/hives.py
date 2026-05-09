from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from api.config import ROOT, settings
from api.database import get_db
from api.models import Alert, Advisory, EnvironmentalData, FarmerDataSource, Hive, User
from api.routers.auth import get_current_user
from sqlalchemy import or_

from api.schemas import (
    AlertResponse,
    DataSourceConfigureSSH,
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


@router.post("", response_model=HiveCreateResponse, status_code=status.HTTP_201_CREATED)
def create_hive(
    body: HiveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a new hive for the logged-in farmer.

    Automatically creates a local watched folder:
        data_sources/{owner_id}/{hive_id}/

    Also returns suggested_remote_folder — the path the farmer should
    create on their external server and point their audio sensor to.
    Convention: farmer_{owner_id}/hive_{hive_id}/
    (relative to whatever base recordings path their server uses)
    """
    owner_id = body.owner_id if (body.owner_id and current_user.role == "admin") else current_user.user_id

    hive = Hive(
        owner_id          = owner_id,
        hive_location     = body.hive_location,
        hive_type         = body.hive_type,
        hive_name         = body.hive_name,
        installation_date = body.installation_date,
        latitude          = body.latitude,
        longitude         = body.longitude,
    )
    db.add(hive)
    db.commit()
    db.refresh(hive)

    # Create the local watched folder for this hive
    folder_path = ROOT / "data_sources" / str(current_user.user_id) / str(hive.hive_id)
    folder_path.mkdir(parents=True, exist_ok=True)

    # Register the data source (starts as folder; farmer can upgrade to SSH)
    data_source = FarmerDataSource(
        user_id     = current_user.user_id,
        hive_id     = hive.hive_id,
        source_type = "folder",
        source_path = str(folder_path),
        is_active   = True,
    )
    db.add(data_source)
    db.commit()

    return HiveCreateResponse(
        hive_id                 = hive.hive_id,
        owner_id                = hive.owner_id,
        hive_name               = hive.hive_name,
        hive_location           = hive.hive_location,
        hive_type               = hive.hive_type,
        installation_date       = hive.installation_date,
        current_state           = hive.current_state,
        latitude                = hive.latitude,
        longitude               = hive.longitude,
        suggested_remote_folder = f"farmer_{owner_id}/hive_{hive.hive_id}",
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
    """Delete a hive. Admin can delete any hive; farmers can only delete their own."""
    q = db.query(Hive).filter(Hive.hive_id == hive_id)
    if current_user.role != "admin":
        q = q.filter(Hive.owner_id == current_user.user_id)

    hive = q.first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    db.delete(hive)
    db.commit()


@router.get("", response_model=list[HiveResponse])
def list_hives(
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List hives.
    - Admin: all hives in the system (optionally filtered by ?search=).
    - Farmer: only their own hives.
    """
    q = db.query(Hive)

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
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
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
        alert_title = (advisory.condition_label if advisory and advisory.condition_label
                       else latest_alert.recommended_action)
        alert_message = (advisory.advisory_text if advisory and advisory.advisory_text
                         else latest_alert.recommended_action)
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
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
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
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    source = db.query(FarmerDataSource).filter(
        FarmerDataSource.hive_id == hive_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Data source not configured")
    return source


@router.post("/{hive_id}/data-source/configure", response_model=DataSourceConfigureResponse)
def configure_ssh_source(
    hive_id: str,
    body: DataSourceConfigureSSH,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register or update the SSH data source for a hive.

    The farmer provides credentials to their external server. We immediately
    test the connection and return the result — if the test fails the config
    is still saved so the farmer can fix it and retry without re-entering
    everything.

    Once configured, the background poller will connect every 30 seconds,
    list new audio files in remote_folder, download them, and run inference.

    Either ssh_password or ssh_private_key must be provided.
    """
    if not body.ssh_password and not body.ssh_private_key:
        raise HTTPException(
            status_code=400,
            detail="Provide either ssh_password or ssh_private_key",
        )

    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.owner_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    ssh_config = {
        "ssh_host":      body.ssh_host,
        "ssh_port":      body.ssh_port,
        "ssh_username":  body.ssh_username,
        "remote_folder": body.remote_folder,
    }
    if body.ssh_password:
        ssh_config["ssh_password"] = body.ssh_password
    if body.ssh_private_key:
        ssh_config["ssh_private_key"] = body.ssh_private_key

    from api.ssh_connector import test_connection
    connection_test = test_connection(ssh_config)

    source = db.query(FarmerDataSource).filter(
        FarmerDataSource.hive_id == hive_id
    ).first()

    if source:
        source.source_type       = "ssh"
        source.source_path       = body.remote_folder
        source.connection_config = ssh_config
        source.is_active         = True
    else:
        source = FarmerDataSource(
            user_id           = current_user.user_id,
            hive_id           = hive_id,
            source_type       = "ssh",
            source_path       = body.remote_folder,
            connection_config = ssh_config,
            is_active         = True,
        )
        db.add(source)

    db.commit()
    db.refresh(source)

    return DataSourceConfigureResponse(
        source_id       = source.source_id,
        hive_id         = hive_id,
        source_type     = "ssh",
        remote_folder   = body.remote_folder,
        connection_test = connection_test,
    )
