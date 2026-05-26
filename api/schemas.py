from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None
    role: str = "farmer"
    server_url: Optional[str] = None  # Farmer's external server URL (e.g., https://abc123.ngrok-free.dev)
    api_key: Optional[str] = None     # API key for accessing farmer's server


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    server_url: Optional[str] = None
    api_key: Optional[str] = None
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
    hive_type: Optional[str] = None
    hive_name: Optional[str] = None
    installation_date: Optional[date] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    owner_id: Optional[str] = None  # admin-only; farmers always own their own hives


class HiveResponse(BaseModel):
    hive_id: str
    owner_id: str
    hive_name: Optional[str]
    hive_location: str
    hive_type: Optional[str]
    installation_date: Optional[date]
    current_state: str
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True


class HiveCreateResponse(HiveResponse):
    """Returned only on POST /hives — includes the suggested remote folder path."""
    suggested_remote_folder: str
    folder_created: bool = False
    folder_creation_error: Optional[str] = None


# ---------------------------------------------------------------------------
# Audio upload response  (returned immediately; inference runs in background)
# ---------------------------------------------------------------------------
class AudioUploadResponse(BaseModel):
    audio_id: str
    message: str
    hive_id: str


# ---------------------------------------------------------------------------
# Advisory
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
    condition_label: Optional[str]
    advisory_text: Optional[str]
    severity: str
    actions: list[AdvisoryActionResponse]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
class AlertResponse(BaseModel):
    alert_id: str
    hive_id: str
    severity_level: str
    recommended_action: Optional[str]
    action_status: str
    alert_timestamp: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Inference result
# ---------------------------------------------------------------------------
class InferenceResponse(BaseModel):
    inference_id: str
    hive_id: str
    hive_state: str
    confidence_score: float
    inference_latency_ms: Optional[int]
    created_at: datetime
    alert: Optional[AlertResponse]
    advisory: Optional[AdvisoryResponse]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# FarmerDataSource
# ---------------------------------------------------------------------------
class DataSourceResponse(BaseModel):
    source_id: str
    hive_id: str
    source_type: str
    source_path: Optional[str]
    last_scanned_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DataSourceConfigureHTTPAPI(BaseModel):
    api_base_url: str
    api_key: str


class DataSourceConfigureResponse(BaseModel):
    source_id: str
    hive_id: str
    source_type: str
    remote_folder: Optional[str] = None
    api_base_url: Optional[str] = None
    connection_test: dict

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Hive update  (PUT /hives/{id})
# ---------------------------------------------------------------------------
class HiveUpdate(BaseModel):
    hive_location: Optional[str] = None
    hive_type: Optional[str] = None
    hive_name: Optional[str] = None
    installation_date: Optional[date] = None
    current_state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ---------------------------------------------------------------------------
# Admin — user management
# ---------------------------------------------------------------------------
class UserDetailResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    role: str
    server_url: Optional[str] = None
    api_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None
    role: str = "farmer"
    server_url: Optional[str] = None
    api_key: Optional[str] = None


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None
    server_url: Optional[str] = None
    api_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Advisory templates
# ---------------------------------------------------------------------------
class AdvisoryTemplateResponse(BaseModel):
    template_id: int
    prediction_code: float
    hive_state: str
    condition_label: str
    advisory_text: str
    advisory_type: str
    severity: str

    class Config:
        from_attributes = True


class AdvisoryTemplateCreate(BaseModel):
    prediction_code: float
    hive_state: str
    condition_label: str
    advisory_text: str
    advisory_type: str = "Reactive"
    severity: str = "info"


class AdvisoryTemplateUpdate(BaseModel):
    condition_label: Optional[str] = None
    advisory_text: Optional[str] = None
    advisory_type: Optional[str] = None
    severity: Optional[str] = None


# ---------------------------------------------------------------------------
# Admin advisory list view
# ---------------------------------------------------------------------------
class AdminAdvisoryResponse(BaseModel):
    advisory_id: str
    hive_id: str
    inference_id: str
    template_id: Optional[int] = None
    advisory_type: str
    condition_label: Optional[str] = None
    advisory_text: Optional[str] = None
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Dashboard  (mobile app summary screen)
# ---------------------------------------------------------------------------
class DashboardStatusCounts(BaseModel):
    normal: int = 0
    pre_swarm: int = 0
    swarm: int = 0
    abscondment: int = 0
    other: int = 0


class DashboardKeyMetrics(BaseModel):
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    population_k_bees: Optional[float] = None
    nectar_flow_kg_per_day: Optional[float] = None


class DashboardResponse(BaseModel):
    total_hives: int
    active_hives: int
    status_counts: DashboardStatusCounts
    key_metrics: DashboardKeyMetrics


# ---------------------------------------------------------------------------
# Mobile alert responses  (top-level /alerts endpoints consumed by the app)
# ---------------------------------------------------------------------------
class MobileAlertResponse(BaseModel):
    id: str
    hive_id: str
    severity: str
    title: str
    date: str
    summary: str


class MobileAlertDetailResponse(BaseModel):
    id: str
    hive_id: str
    severity: str
    title: str
    time: str
    details: str
    acknowledged: bool


# ---------------------------------------------------------------------------
# Enriched hive detail  (GET /hives/{hive_id} used by the mobile detail screen)
# ---------------------------------------------------------------------------
class MetricPoint(BaseModel):
    time_label: str
    temperature_c: float
    humidity_percent: float


class HiveDetailResponse(HiveResponse):
    alert_title: Optional[str] = None
    alert_message: Optional[str] = None
    acknowledged: bool = False
    metric_series: list[MetricPoint] = []


# ---------------------------------------------------------------------------
# System logs
# ---------------------------------------------------------------------------
class SystemLogResponse(BaseModel):
    log_id:     str
    level:      str
    event_type: str
    message:    str
    details:    Optional[dict] = None
    hive_id:    Optional[str] = None
    user_id:    Optional[str] = None
    audio_id:   Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
