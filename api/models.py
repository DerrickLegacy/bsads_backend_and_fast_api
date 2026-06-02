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

    user_id                   = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    full_name                 = Column(String(100), nullable=False)
    email                     = Column(String(100), unique=True, nullable=False, index=True)
    email_verified_at         = Column(DateTime, nullable=True)
    phone                     = Column(String(20), unique=True, nullable=True)
    address                   = Column(Text, nullable=True)
    password_hash             = Column(String(255), nullable=False)
    role                      = Column(String(30), nullable=False, default="farmer")
    two_factor_secret         = Column(Text, nullable=True)
    two_factor_recovery_codes = Column(Text, nullable=True)
    remember_token            = Column(String(100), nullable=True)
    device_token              = Column(String(500), nullable=True)
    device_token_updated_at   = Column(DateTime, nullable=True)
    # Farmer's external data source server credentials (HTTP API)
    server_url                = Column(String(255), nullable=True)  # e.g., https://abc123.ngrok-free.dev
    api_key                   = Column(String(255), nullable=True)  # e.g., f47ac10b-58cc-4372-a567-0e02b2c3d479
    created_at                = Column(DateTime, default=datetime.utcnow)
    updated_at                = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hives        = relationship("Hive", back_populates="owner")
    data_sources = relationship("FarmerDataSource", back_populates="user")


# ---------------------------------------------------------------------------
# Hive  (one farmer → many hives)
# ---------------------------------------------------------------------------
class Hive(Base):
    __tablename__ = "hives"

    hive_id           = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    owner_id          = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    hive_name         = Column(String(100), nullable=True)
    hive_location     = Column(String(150), nullable=False)
    hive_type         = Column(String(50), nullable=True)
    installation_date = Column(Date, nullable=True)
    current_state     = Column(String(50), nullable=False, default="unknown")
    latitude          = Column(Numeric(9, 6), nullable=True)
    longitude         = Column(Numeric(9, 6), nullable=True)
    is_deleted        = Column(Boolean, nullable=False, default=False)
    deleted_at        = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner            = relationship("User", back_populates="hives")
    audio_sources    = relationship("AudioSource", back_populates="hive")
    inference_results = relationship("InferenceResult", back_populates="hive")
    alerts           = relationship("Alert", back_populates="hive")
    advisories       = relationship("Advisory", back_populates="hive")
    env_records      = relationship("EnvironmentalData", back_populates="hive")


# ---------------------------------------------------------------------------
# AudioSource
# status lifecycle:  pending → processing → processed | failed
# ---------------------------------------------------------------------------
class AudioSource(Base):
    __tablename__ = "audio_sources"

    audio_id            = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id             = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id", ondelete="CASCADE"), nullable=False)
    source_url          = Column(String(255), nullable=False)
    file_format         = Column(String(20), nullable=False, default="wav")
    duration_seconds    = Column(Numeric(6, 2), nullable=True)
    captured_at         = Column(DateTime, nullable=True)
    ingestion_timestamp = Column(DateTime, default=datetime.utcnow)
    status              = Column(String(20), nullable=False, default="pending")

    hive = relationship("Hive", back_populates="audio_sources")


# ---------------------------------------------------------------------------
# EnvironmentalData
# ---------------------------------------------------------------------------
class EnvironmentalData(Base):
    __tablename__ = "environmental_data"

    env_record_id          = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id                = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id", ondelete="CASCADE"), nullable=False)
    temperature            = Column(Numeric(5, 2), nullable=True)
    humidity               = Column(Numeric(5, 2), nullable=True)
    population_k_bees      = Column(Numeric(6, 2), nullable=True)
    nectar_flow_kg_per_day = Column(Numeric(6, 2), nullable=True)
    recorded_at            = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", back_populates="env_records")


# ---------------------------------------------------------------------------
# AdvisoryTemplate  (static lookup — one row per hive_state classification)
# Managed via the beehive-app admin panel.
# ---------------------------------------------------------------------------
class AdvisoryTemplate(Base):
    __tablename__ = "advisory_templates"

    template_id     = Column(BigInteger, primary_key=True, autoincrement=True)
    prediction_code = Column(Numeric, nullable=False, unique=True)
    hive_state      = Column(String(50), nullable=False, unique=True)
    condition_label = Column(String(100), nullable=False)
    advisory_text   = Column(Text, nullable=False)
    advisory_type   = Column(String(30), nullable=False, default="Reactive")
    severity        = Column(String(20), nullable=False, default="info")
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    advisories = relationship("Advisory", back_populates="template")


# ---------------------------------------------------------------------------
# InferenceResult  (ML model output — one per processed audio file)
# hive_state unified vocabulary: normal | pre_swarm | swarm | abscondment |
#   missing_queen | queenbee_present | pest_infested | external_noise | uncertain
# ---------------------------------------------------------------------------
class InferenceResult(Base):
    __tablename__ = "inference_results"

    inference_id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id              = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id", ondelete="CASCADE"), nullable=False)
    audio_id             = Column(UUID(as_uuid=False), ForeignKey("audio_sources.audio_id", ondelete="SET NULL"), nullable=True)
    hive_state           = Column(String(50), nullable=False)
    confidence_score     = Column(Numeric(5, 4), nullable=False)
    inference_latency_ms = Column(Numeric, nullable=True)
    analyzed_at          = Column(DateTime, default=datetime.utcnow)
    created_at           = Column(DateTime, default=datetime.utcnow)

    hive     = relationship("Hive", back_populates="inference_results")
    alert    = relationship("Alert", back_populates="inference", uselist=False)
    advisory = relationship("Advisory", back_populates="inference", uselist=False)


# ---------------------------------------------------------------------------
# Advisory  (generated per-inference — linked to a template for traceability)
# ---------------------------------------------------------------------------
class Advisory(Base):
    __tablename__ = "advisories"

    advisory_id     = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    inference_id    = Column(UUID(as_uuid=False), ForeignKey("inference_results.inference_id", ondelete="CASCADE"), nullable=False)
    hive_id         = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id", ondelete="CASCADE"), nullable=False)
    template_id     = Column(BigInteger, ForeignKey("advisory_templates.template_id", ondelete="SET NULL"), nullable=True)
    advisory_type   = Column(String(30), nullable=False, default="Reactive")
    condition_label = Column(String(100), nullable=True)
    advisory_text   = Column(Text, nullable=True)
    severity        = Column(String(20), nullable=False, default="info")
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hive      = relationship("Hive", back_populates="advisories")
    inference = relationship("InferenceResult", back_populates="advisory")
    template  = relationship("AdvisoryTemplate", back_populates="advisories")
    actions   = relationship("AdvisoryAction", back_populates="advisory")


# ---------------------------------------------------------------------------
# AdvisoryAction  (individual checklist items inside a generated advisory)
# ---------------------------------------------------------------------------
class AdvisoryAction(Base):
    __tablename__ = "advisory_actions"

    action_id          = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    advisory_id        = Column(UUID(as_uuid=False), ForeignKey("advisories.advisory_id", ondelete="CASCADE"), nullable=False)
    action_description = Column(Text, nullable=False)
    priority_level     = Column(String(20), nullable=False, default="medium")
    status             = Column(String(20), nullable=False, default="pending")
    created_at         = Column(DateTime, default=datetime.utcnow)

    advisory = relationship("Advisory", back_populates="actions")


# ---------------------------------------------------------------------------
# Alert  (raised when inference warrants immediate farmer attention)
# action_status lifecycle:  pending → sent → acknowledged
# ---------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    alert_id           = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id            = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id", ondelete="CASCADE"), nullable=False)
    inference_id       = Column(UUID(as_uuid=False), ForeignKey("inference_results.inference_id", ondelete="CASCADE"), nullable=False)
    advisory_id        = Column(UUID(as_uuid=False), ForeignKey("advisories.advisory_id", ondelete="SET NULL"), nullable=True)
    severity_level     = Column(String(20), nullable=False)
    recommended_action = Column(Text, nullable=True)
    action_status      = Column(String(20), nullable=False, default="pending")
    alert_timestamp    = Column(DateTime, default=datetime.utcnow)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hive      = relationship("Hive", back_populates="alerts")
    inference = relationship("InferenceResult", back_populates="alert")
    advisory  = relationship("Advisory", foreign_keys=[advisory_id], primaryjoin="Alert.advisory_id == Advisory.advisory_id", uselist=False)


# ---------------------------------------------------------------------------
# FarmerDataSource  (how each farmer's audio reaches the system)
# source_type:  http_api (HTTP REST API with API key authentication)
# ---------------------------------------------------------------------------
class FarmerDataSource(Base):
    __tablename__ = "farmer_data_sources"

    source_id         = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id           = Column(UUID(as_uuid=False), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    hive_id           = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id", ondelete="CASCADE"), nullable=False, unique=True)
    source_type       = Column(String(50), nullable=False, default="folder")
    source_path       = Column(Text, nullable=True)
    connection_config = Column(JSONB, nullable=True)
    last_scanned_at   = Column(DateTime, nullable=True)
    is_active         = Column(Boolean, nullable=False, default=True)
    created_at        = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", backref="data_source", uselist=False)
    user = relationship("User", back_populates="data_sources")


# ---------------------------------------------------------------------------
# SystemLog  (audit trail for every significant event in the system)
# level:      info | warning | error | critical
# event_type: inference | poller | auth | upload | http_api | advisory | system
# ---------------------------------------------------------------------------
class SystemLog(Base):
    __tablename__ = "system_logs"

    log_id     = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    level      = Column(String(20),  nullable=False, default="info")
    event_type = Column(String(50),  nullable=False)
    message    = Column(Text,        nullable=False)
    details    = Column(JSONB,       nullable=True)   # traceback, ids, extra context
    hive_id    = Column(UUID(as_uuid=False), ForeignKey("hives.hive_id",          ondelete="SET NULL"), nullable=True)
    user_id    = Column(UUID(as_uuid=False), ForeignKey("users.user_id",          ondelete="SET NULL"), nullable=True)
    audio_id   = Column(UUID(as_uuid=False), ForeignKey("audio_sources.audio_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
