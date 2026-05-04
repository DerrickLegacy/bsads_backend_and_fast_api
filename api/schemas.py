from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    fullname: str
    email: EmailStr
    password: str
    telephone_number: Optional[str] = None
    role: str = "farmer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: int
    fullname: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Hive
# ---------------------------------------------------------------------------
class HiveCreate(BaseModel):
    hive_location: str
    hive_type: str
    installation_date: Optional[datetime] = None


class HiveResponse(BaseModel):
    hive_id: int
    user_id: int
    hive_location: str
    hive_type: str
    installation_date: Optional[datetime]
    current_state: str

    class Config:
        from_attributes = True


class HiveCreateResponse(HiveResponse):
    """Returned only on POST /hives — includes the suggested remote folder path.

    The mobile app should show this to the farmer when they go to configure
    their SSH data source, so they know exactly where on their server to
    point their audio sensor.

    Convention (relative to the farmer's recording base path):
        farmer_{user_id}/hive_{hive_id}/
    e.g. on the simulation server: /home/farmer/recordings/farmer_1/hive_1/
    """
    suggested_remote_folder: str


# ---------------------------------------------------------------------------
# Audio upload response  (returned immediately after upload)
# The actual inference result comes via the inferences endpoint
# ---------------------------------------------------------------------------
class AudioUploadResponse(BaseModel):
    audio_id: str
    message: str
    hive_id: int


# ---------------------------------------------------------------------------
# InferenceResult  (what the mobile app reads after processing)
# ---------------------------------------------------------------------------
class AdvisoryActionResponse(BaseModel):
    action_id: str
    action_description: str
    priority_level: str
    status: str

    class Config:
        from_attributes = True


class AdvisoryResponse(BaseModel):
    advisory_id: str
    advisory_type: str
    actions: list[AdvisoryActionResponse]

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    alert_id: str
    hive_id: int
    severity_level: str
    recommended_action: str
    action_status: str
    generated_at: datetime

    class Config:
        from_attributes = True


class InferenceResponse(BaseModel):
    inference_id: str
    hive_id: int
    hive_state: str
    confidence_score: float
    inference_latency_ms: Optional[int]
    created_at: datetime
    alert: Optional[AlertResponse]
    advisory: Optional[AdvisoryResponse]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# FarmerDataSource  (returned when farmer checks their data source config)
# ---------------------------------------------------------------------------
class DataSourceResponse(BaseModel):
    source_id: str
    hive_id: int
    source_type: str
    source_path: Optional[str]
    last_scanned_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# SSH data source configuration  (farmer registers their remote server)
# Either ssh_password OR ssh_private_key must be provided — not both.
# ---------------------------------------------------------------------------
class DataSourceConfigureSSH(BaseModel):
    ssh_host: str
    ssh_port: int = 22
    ssh_username: str
    ssh_password: Optional[str] = None
    ssh_private_key: Optional[str] = None   # full PEM string
    remote_folder: str                       # absolute path on the remote server
                                             # recommended convention:
                                             # /home/farmer/recordings/farmer_{user_id}/hive_{hive_id}


class DataSourceConfigureResponse(BaseModel):
    source_id: str
    hive_id: int
    source_type: str
    remote_folder: str
    connection_test: dict   # {"ok": True} or {"ok": False, "error": "..."}

    class Config:
        from_attributes = True
