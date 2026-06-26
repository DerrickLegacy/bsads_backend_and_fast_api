from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, Field
import re


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone: str
    address: str
    role: str = "farmer"
    # Optional: Admin can assign these after registration
    server_url: Optional[str] = None
    api_key: Optional[str] = None
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate API key format - must be UUID-like or at least 32 alphanumeric characters with hyphens"""
        # Allow None/empty for admin assignment flow
        if not v or v == "string":  # Also skip default "string" placeholder
            return None
            
        if len(v.strip()) < 32:
            raise ValueError('API key must be at least 32 characters long')
        
        # Check if it's a valid UUID format (with or without hyphens)
        uuid_pattern = r'^[a-fA-F0-9]{8}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{4}-?[a-fA-F0-9]{12}$'
        
        # Remove whitespace
        cleaned = v.strip()
        
        # Check if it matches UUID pattern
        if re.match(uuid_pattern, cleaned):
            return cleaned
        
        # If not UUID format, check if it's at least 32 alphanumeric/hyphen/underscore characters
        if len(cleaned) >= 32 and re.match(r'^[a-zA-Z0-9_-]+$', cleaned):
            return cleaned
        
        raise ValueError('API key must be a valid UUID format (e.g., f47ac10b-58cc-4372-a567-0e02b2c3d479) or at least 32 alphanumeric characters')
    
    @field_validator('server_url')
    @classmethod
    def validate_server_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate server URL format"""
        # Allow None/empty for admin assignment flow
        if not v or v == "string":  # Also skip default "string" placeholder
            return None
            
        if len(v.strip()) < 10:
            raise ValueError('Server URL must be a valid URL')
        
        cleaned = v.strip()
        
        # Check if it starts with http:// or https://
        if not (cleaned.startswith('http://') or cleaned.startswith('https://')):
            raise ValueError('Server URL must start with http:// or https://')
        
        return cleaned
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format"""
        if not v or len(v.strip()) < 10:
            raise ValueError('Phone number must be at least 10 characters')
        
        # Remove spaces and common separators for validation
        cleaned = re.sub(r'[\s\-\(\)]', '', v)
        
        if not re.match(r'^\+?[0-9]{10,15}$', cleaned):
            raise ValueError('Phone number must contain 10-15 digits (with optional + prefix)')
        
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    phone: str | None = None
    address: str | None = None
    server_url: Optional[str] = None
    api_key: Optional[str] = None
    profile_photo_url: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LogoutResponse(BaseModel):
    detail: str = "Logged out successfully"


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
    # admin-only; farmers always own their own hives
    owner_id: Optional[str] = None


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
    # Timestamp of the most recent inference
    last_inference_at: Optional[datetime] = None

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
# Advisory (legacy - kept for backward compatibility with old inference results)
# ---------------------------------------------------------------------------
class AdvisoryActionResponse(BaseModel):
    action_id: str
    action_description: str
    priority_level: str
    status: str

    class Config:
        from_attributes = True


class AdvisoryResponse(BaseModel):
    """Legacy advisory response - now returns inference-specific actions"""
    advisory_id: str
    advisory_type: str
    condition_label: Optional[str]
    advisory_text: Optional[str]
    severity: str
    actions: list[AdvisoryActionResponse] = []

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
# Advisory templates (classification definitions only)
# ---------------------------------------------------------------------------
class AdvisoryTemplateResponse(BaseModel):
    template_id: int
    prediction_code: float
    hive_state: str
    advisory_type: str
    severity: str
    min_confidence_threshold: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class AdvisoryTemplateCreate(BaseModel):
    prediction_code: float
    hive_state: str
    advisory_type: str = "Reactive"
    severity: str = "info"
    min_confidence_threshold: float = 0.70
    description: Optional[str] = None


class AdvisoryTemplateUpdate(BaseModel):
    advisory_type: Optional[str] = None
    severity: Optional[str] = None
    min_confidence_threshold: Optional[float] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Advisories (reusable action library)
# ---------------------------------------------------------------------------
class AdvisoryLibraryResponse(BaseModel):
    advisory_id: str
    template_id: int
    action_title: str
    action_description: str
    priority_level: str
    confidence_threshold_min: float
    confidence_threshold_max: float
    action_order: int
    is_active: bool

    class Config:
        from_attributes = True


class AdvisoryLibraryCreate(BaseModel):
    template_id: int
    action_title: str
    action_description: str
    priority_level: str = "medium"
    confidence_threshold_min: float = 0.70
    confidence_threshold_max: float = 1.00
    action_order: int = 1
    is_active: bool = True


class AdvisoryLibraryUpdate(BaseModel):
    action_title: Optional[str] = None
    action_description: Optional[str] = None
    priority_level: Optional[str] = None
    confidence_threshold_min: Optional[float] = None
    confidence_threshold_max: Optional[float] = None
    action_order: Optional[int] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Advisory actions (inference-specific suggested actions)
# ---------------------------------------------------------------------------
class AdvisoryActionSuggestedResponse(BaseModel):
    """Actions suggested for a specific inference"""
    action_id: str
    inference_id: str
    hive_id: str
    template_id: int
    hive_state: str  # From template
    confidence_score: float
    action_title: str
    action_description: str
    priority_level: str
    status: str
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdvisoryActionUpdateStatus(BaseModel):
    """Update action status by farmer"""
    status: str  # pending, in_progress, completed, skipped
    notes: Optional[str] = None


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
    missing_queen: int = 0
    queenbee_present: int = 0
    pest_infested: int = 0
    external_noise: int = 0
    uncertain: int = 0
    other: int = 0


class DashboardKeyMetrics(BaseModel):
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None


class DashboardSilentHive(BaseModel):
    hive_id: str
    hive_name: Optional[str] = None
    last_audio_at: Optional[str] = None   # ISO timestamp or null
    hours_silent: Optional[float] = None


class DashboardResponse(BaseModel):
    total_hives: int
    active_hives: int
    status_counts: DashboardStatusCounts
    key_metrics: DashboardKeyMetrics
    recordings_today: int = 0
    silent_hives: list[DashboardSilentHive] = []
    pending_alerts: int = 0


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
    alertStatus: str = "pending"  # "pending", "acknowledged", "sent"
    viewed_at: Optional[str] = None  # ISO timestamp when farmer first viewed it


class AudioRecordingResponse(BaseModel):
    id: str
    file_path: str
    duration_seconds: int
    recorded_at: str


class AdvisoryActionItem(BaseModel):
    id: str
    description: str
    priority: str  # "High", "Medium", "Low"


class AdvisoryDetail(BaseModel):
    id: str
    alert_id: str
    type: str  # "Preventive" or "Reactive"
    summary: str
    actions: list[AdvisoryActionItem] = []


class MobileAlertDetailResponse(BaseModel):
    id: str
    hive_id: str
    hive_name: Optional[str] = None
    severity: str
    title: str
    time: str
    created_at: Optional[str] = None
    details: str
    acknowledged: bool
    audio_recording: Optional[AudioRecordingResponse] = None
    advisory: Optional[AdvisoryDetail] = None
    prediction_details: Optional[dict] = None  # Top-3 predictions with confidence scores


# ---------------------------------------------------------------------------
# Enriched hive detail  (GET /hives/{hive_id} used by the mobile detail screen)
# ---------------------------------------------------------------------------
class MetricPoint(BaseModel):
    time_label: str
    temperature_c: float
    humidity_percent: float


class WeatherData(BaseModel):
    temperature: float
    humidity: float
    timestamp: str
    weather_description: Optional[str] = None


class HiveDetailResponse(HiveResponse):
    alert_title: Optional[str] = None
    alert_message: Optional[str] = None
    acknowledged: bool = False
    # Confidence score from latest inference
    confidence_score: Optional[float] = None
    # Full prediction details from latest inference (predicted_class + top_predictions)
    prediction_details: Optional[dict] = None
    metric_series: list[MetricPoint] = []
    weather: Optional[WeatherData] = None  # Current weather at hive location
    # Human-readable last analysis time
    last_analysis_time: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Admin Keys (for external data source servers)
# ---------------------------------------------------------------------------
class AdminKeyResponse(BaseModel):
    admin_key_id: str
    server_name: str
    server_url: Optional[str] = None
    admin_key: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminKeyCreate(BaseModel):
    server_name: str
    server_url: Optional[str] = None
    admin_key: str
    description: Optional[str] = None
    is_active: bool = True


class AdminKeyUpdate(BaseModel):
    server_name: Optional[str] = None
    server_url: Optional[str] = None
    admin_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Admin — Assign API tokens to farmers
# ---------------------------------------------------------------------------
class AssignFarmerTokenRequest(BaseModel):
    admin_key: str  # The admin key to use for this server
    server_url: str  # The server URL to call


class AssignFarmerTokenResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    server_url: str
    api_key: str
    assigned_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Push notifications
# ---------------------------------------------------------------------------
class PushNotificationDeviceRegister(BaseModel):
    token: str
    device_id: str
    platform: str


class PushNotificationDeviceResponse(BaseModel):
    id: int
    user_id: str
    token: str
    device_id: str
    platform: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
