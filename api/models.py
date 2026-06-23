import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Numeric, String, Text, JSON, BigInteger, Date
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from api.database import Base


def new_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User  (farmers, admins, extension officers — unified with Laravel users)
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    email_verified_at = Column(DateTime, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    address = Column(Text, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="farmer")
    two_factor_secret = Column(Text, nullable=True)
    two_factor_recovery_codes = Column(Text, nullable=True)
    remember_token = Column(String(100), nullable=True)
    device_token = Column(String(500), nullable=True)
    device_token_updated_at = Column(DateTime, nullable=True)
    # Farmer's external data source server credentials (HTTP API)
    # e.g., https://abc123.ngrok-free.dev
    # NULLABLE: Admin assigns these after user registration
    server_url = Column(String(255), nullable=True)
    # e.g., f47ac10b-58cc-4372-a567-0e02b2c3d479
    # NULLABLE: Admin assigns these after user registration
    api_key = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    hives = relationship("Hive", back_populates="owner")
    data_sources = relationship("FarmerDataSource", back_populates="user")


# ---------------------------------------------------------------------------
# Hive  (one farmer → many hives)
# ---------------------------------------------------------------------------
class Hive(Base):
    __tablename__ = "hives"

    hive_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey(
        "users.user_id", ondelete="CASCADE"), nullable=False)
    hive_name = Column(String(100), nullable=True)
    hive_location = Column(String(150), nullable=False)
    hive_type = Column(String(50), nullable=True)
    installation_date = Column(Date, nullable=True)
    current_state = Column(String(50), nullable=False, default="unknown")
    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="hives")
    audio_sources = relationship("AudioSource", back_populates="hive")
    inference_results = relationship("InferenceResult", back_populates="hive")
    alerts = relationship("Alert", back_populates="hive")
    env_records = relationship("EnvironmentalData", back_populates="hive")


# ---------------------------------------------------------------------------
# AudioSource
# status lifecycle:  pending → processing → processed | failed
# ---------------------------------------------------------------------------
class AudioSource(Base):
    __tablename__ = "audio_sources"

    audio_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False)
    source_url = Column(String(255), nullable=False)
    file_format = Column(String(20), nullable=False, default="wav")
    duration_seconds = Column(Numeric(6, 2), nullable=True)
    captured_at = Column(DateTime, nullable=True)
    ingestion_timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    hive = relationship("Hive", back_populates="audio_sources")


# ---------------------------------------------------------------------------
# EnvironmentalData (collective/external weather)
# ---------------------------------------------------------------------------
class EnvironmentalData(Base):
    __tablename__ = "environmental_data"

    env_record_id = Column(UUID(as_uuid=False),
                           primary_key=True, default=new_uuid)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False)
    temperature = Column(Numeric(5, 2), nullable=True)
    humidity = Column(Numeric(5, 2), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    hive = relationship("Hive", back_populates="env_records")


# ---------------------------------------------------------------------------
# HiveCondition (internal hive sensor readings - 3 zones)
# ---------------------------------------------------------------------------
class HiveCondition(Base):
    __tablename__ = "hive_conditions"

    condition_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False)
    audio_id = Column(UUID(as_uuid=False), ForeignKey(
        "audio_sources.audio_id", ondelete="SET NULL"), nullable=True)
    
    # Three-zone temperature readings (in Celsius)
    temp_honey = Column(Numeric(5, 2), nullable=True)     # Honey storage zone
    temp_brood = Column(Numeric(5, 2), nullable=True)     # Brood rearing zone
    temp_exterior = Column(Numeric(5, 2), nullable=True)  # External/entrance
    
    # Three-zone humidity readings (percentage)
    humidity_honey = Column(Numeric(5, 2), nullable=True)
    humidity_brood = Column(Numeric(5, 2), nullable=True)
    humidity_exterior = Column(Numeric(5, 2), nullable=True)
    
    recorded_at = Column(DateTime, nullable=False)  # From device timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    hive = relationship("Hive")
    audio = relationship("AudioSource")


# ---------------------------------------------------------------------------
# AdvisoryTemplate  (classification definitions only)
# Managed via the beehive-app admin panel.
# ---------------------------------------------------------------------------
class AdvisoryTemplate(Base):
    __tablename__ = "advisory_templates"

    template_id = Column(BigInteger, primary_key=True, autoincrement=True)
    prediction_code = Column(Numeric, nullable=False, unique=True)
    hive_state = Column(String(50), nullable=False, unique=True)
    advisory_type = Column(String(30), nullable=False, default="Reactive")
    severity = Column(String(20), nullable=False, default="info")
    min_confidence_threshold = Column(Numeric(5, 4), nullable=False, default=0.70)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    advisories = relationship("Advisory", back_populates="template")


# ---------------------------------------------------------------------------
# InferenceResult  (ML model output — one per processed audio file)
# hive_state unified vocabulary: normal | pre_swarm | swarm | abscondment |
#   missing_queen | queenbee_present | pest_infested | external_noise | uncertain
# ---------------------------------------------------------------------------
class InferenceResult(Base):
    __tablename__ = "inference_results"

    inference_id = Column(UUID(as_uuid=False),
                          primary_key=True, default=new_uuid)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False)
    audio_id = Column(UUID(as_uuid=False), ForeignKey(
        "audio_sources.audio_id", ondelete="SET NULL"), nullable=True)
    hive_state = Column(String(50), nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=False)
    prediction_details = Column(JSONB, nullable=True)  # Stores top-3 predictions with confidences
    inference_latency_ms = Column(Numeric, nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", back_populates="inference_results")
    alert = relationship("Alert", back_populates="inference", uselist=False)
    advisory_actions = relationship("AdvisoryAction", back_populates="inference")


# ---------------------------------------------------------------------------
# Advisory  (reusable action library for each classification)
# ---------------------------------------------------------------------------
class Advisory(Base):
    __tablename__ = "advisories"

    advisory_id = Column(UUID(as_uuid=False),
                         primary_key=True, default=new_uuid)
    template_id = Column(BigInteger, ForeignKey(
        "advisory_templates.template_id", ondelete="CASCADE"), nullable=False)
    action_title = Column(String(200), nullable=False)
    action_description = Column(Text, nullable=False)
    priority_level = Column(String(20), nullable=False, default="medium")
    confidence_threshold_min = Column(Numeric(5, 4), nullable=False, default=0.70)
    confidence_threshold_max = Column(Numeric(5, 4), nullable=False, default=1.00)
    action_order = Column(BigInteger, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    template = relationship("AdvisoryTemplate", back_populates="advisories")
    actions = relationship("AdvisoryAction", back_populates="advisory")


# ---------------------------------------------------------------------------
# AdvisoryAction  (specific actions suggested per hive inference)
# ---------------------------------------------------------------------------
class AdvisoryAction(Base):
    __tablename__ = "advisory_actions"

    action_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    inference_id = Column(UUID(as_uuid=False), ForeignKey(
        "inference_results.inference_id", ondelete="CASCADE"), nullable=True)  # nullable for rule-based alerts
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False)
    advisory_id = Column(UUID(as_uuid=False), ForeignKey(
        "advisories.advisory_id", ondelete="CASCADE"), nullable=False)
    template_id = Column(BigInteger, ForeignKey(
        "advisory_templates.template_id", ondelete="CASCADE"), nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=False)
    action_title = Column(String(200), nullable=False)
    action_description = Column(Text, nullable=False)
    priority_level = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="pending")
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    inference = relationship("InferenceResult")
    hive = relationship("Hive")
    advisory = relationship("Advisory", back_populates="actions")
    template = relationship("AdvisoryTemplate")


# ---------------------------------------------------------------------------
# Alert  (raised when inference warrants immediate farmer attention)
# action_status lifecycle:  pending → sent → acknowledged
# ---------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False)
    inference_id = Column(UUID(as_uuid=False), ForeignKey(
        "inference_results.inference_id", ondelete="CASCADE"), nullable=True)  # nullable for rule-based alerts
    severity_level = Column(String(20), nullable=False)
    recommended_action = Column(Text, nullable=True)
    action_status = Column(String(20), nullable=False, default="pending")
    alert_timestamp = Column(DateTime, default=datetime.utcnow)
    viewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    hive = relationship("Hive", back_populates="alerts")
    inference = relationship("InferenceResult", back_populates="alert")


# ---------------------------------------------------------------------------
# FarmerDataSource  (how each farmer's audio reaches the system)
# source_type:  http_api (HTTP REST API with API key authentication)
# ---------------------------------------------------------------------------
class FarmerDataSource(Base):
    __tablename__ = "farmer_data_sources"

    source_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey(
        "users.user_id", ondelete="CASCADE"), nullable=False)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id", ondelete="CASCADE"), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False, default="folder")
    source_path = Column(Text, nullable=True)
    connection_config = Column(JSONB, nullable=True)
    last_scanned_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", backref="data_source", uselist=False)
    user = relationship("User", back_populates="data_sources")


# ---------------------------------------------------------------------------
# SystemLog  (audit trail for every significant event in the system)
# level:      info | warning | error | critical
# event_type: inference | poller | auth | upload | http_api | advisory | system
# ---------------------------------------------------------------------------
class SystemLog(Base):
    __tablename__ = "system_logs"

    log_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    level = Column(String(20),  nullable=False, default="info")
    event_type = Column(String(50),  nullable=False)
    message = Column(Text,        nullable=False)
    # traceback, ids, extra context
    details = Column(JSONB,       nullable=True)
    hive_id = Column(UUID(as_uuid=False), ForeignKey(
        "hives.hive_id",          ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey(
        "users.user_id",          ondelete="SET NULL"), nullable=True)
    audio_id = Column(UUID(as_uuid=False), ForeignKey(
        "audio_sources.audio_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ---------------------------------------------------------------------------
# SystemSettings  (app-wide key-value configuration store)
# ---------------------------------------------------------------------------
class PushNotificationDevice(Base):
    __tablename__ = "push_notification_devices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey(
        "users.user_id", ondelete="CASCADE"
    ), nullable=False, index=True)
    token = Column(String(500), nullable=False)
    device_id = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    user = relationship("User", backref="push_devices")


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False, unique=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# AdminKeys  (stores admin keys for external data source servers)
# ---------------------------------------------------------------------------
class AdminKey(Base):
    __tablename__ = "admin_keys"

    admin_key_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    server_name = Column(String(100), nullable=False)
    server_url = Column(String(255), nullable=True)
    admin_key = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=False), ForeignKey(
        "users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    creator = relationship("User")
