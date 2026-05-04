from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.config import ROOT, settings
from api.database import get_db
from api.models import FarmerDataSource, Hive, User
from api.routers.auth import get_current_user
from api.schemas import (
    DataSourceConfigureSSH,
    DataSourceConfigureResponse,
    DataSourceResponse,
    HiveCreate,
    HiveCreateResponse,
    HiveResponse,
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
        data_sources/{user_id}/{hive_id}/

    Also returns suggested_remote_folder — the path the farmer should
    create on their external server and point their audio sensor to.
    Convention: farmer_{user_id}/hive_{hive_id}/
    (relative to whatever base recordings path their server uses)
    """
    hive = Hive(
        user_id           = current_user.user_id,
        hive_location     = body.hive_location,
        hive_type         = body.hive_type,
        installation_date = body.installation_date,
    )
    db.add(hive)
    db.commit()
    db.refresh(hive)

    # Create the local watched folder for this hive
    folder_path = ROOT / "data_sources" / str(current_user.user_id) / str(hive.hive_id)
    folder_path.mkdir(parents=True, exist_ok=True)

    # Register the data source in the database (starts as folder; farmer can upgrade to SSH)
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
        hive_id                  = hive.hive_id,
        user_id                  = hive.user_id,
        hive_location            = hive.hive_location,
        hive_type                = hive.hive_type,
        installation_date        = hive.installation_date,
        current_state            = hive.current_state,
        suggested_remote_folder  = f"farmer_{current_user.user_id}/hive_{hive.hive_id}",
    )


@router.get("", response_model=list[HiveResponse])
def list_hives(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all hives belonging to the logged-in farmer."""
    return db.query(Hive).filter(Hive.user_id == current_user.user_id).all()


@router.get("/{hive_id}", response_model=HiveResponse)
def get_hive(
    hive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.user_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")
    return hive


@router.get("/{hive_id}/data-source", response_model=DataSourceResponse)
def get_data_source(
    hive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the data source info for a hive — including the folder path
    to drop audio files into and when it was last scanned.
    """
    hive = db.query(Hive).filter(
        Hive.hive_id == hive_id,
        Hive.user_id == current_user.user_id,
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
    hive_id: int,
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
        Hive.user_id == current_user.user_id,
    ).first()
    if not hive:
        raise HTTPException(status_code=404, detail="Hive not found")

    # Build the config dict that gets stored and used by the poller/connector
    ssh_config = {
        "ssh_host":        body.ssh_host,
        "ssh_port":        body.ssh_port,
        "ssh_username":    body.ssh_username,
        "remote_folder":   body.remote_folder,
    }
    if body.ssh_password:
        ssh_config["ssh_password"] = body.ssh_password
    if body.ssh_private_key:
        ssh_config["ssh_private_key"] = body.ssh_private_key

    # Test the connection before saving so the farmer gets immediate feedback
    from api.ssh_connector import test_connection
    connection_test = test_connection(ssh_config)

    # Save / update the data source record
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
