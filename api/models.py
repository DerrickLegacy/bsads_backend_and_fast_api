import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from api.database import Base


# ---------------------------------------------------------------------------
# Helper: default UUID for primary keys
# ---------------------------------------------------------------------------
def new_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User  (farmer account)
# 'users' avoids the reserved word 'user' in PostgreSQL
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    fullname = Column(String(100), nullable=False)
    telephone_number = Column(String(15))
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), default="farmer")   # farmer | admin
    created_at = Column(DateTime, default=datetime.utcnow)

    hives = relationship("Hive", back_populates="owner")


# ---------------------------------------------------------------------------
# Hive  (one farmer → many hives)
# ---------------------------------------------------------------------------
class Hive(Base):
    __tablename__ = "hives"

    hive_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    hive_location = Column(String(150))
    hive_type = Column(String(50))
    installation_date = Column(DateTime)
    current_state = Column(String(30), default="unknown")

    owner = relationship("User", back_populates="hives")
    audio_sources = relationship("AudioSource", back_populates="hive")
    inference_results = relationship("InferenceResult", back_populates="hive")
    alerts = relationship("Alert", back_populates="hive")
    advisories = relationship("Advisory", back_populates="hive")
    env_records = relationship("EnvironmentalData", back_populates="hive")
    image_spectra = relationship("ImageSpectrum", back_populates="hive")


# ---------------------------------------------------------------------------
# AudioSource  (every uploaded audio file)
# source_url = path/URL where the file is stored on the server
# status: pending → processing → processed | failed
# ---------------------------------------------------------------------------
class AudioSource(Base):
    __tablename__ = "audio_sources"

    audio_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    source_url = Column(String(255), nullable=False)
    file_format = Column(String(20), default="wav")
    duration_second = Column(Numeric(6, 2))
    captured_at = Column(DateTime, default=datetime.utcnow)
    ingestion_time_stamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")

    hive = relationship("Hive", back_populates="audio_sources")
    feature_vectors = relationship(
        "FeatureVector", back_populates="audio_source")
    image_spectra = relationship(
        "ImageSpectrum", back_populates="audio_source")


# ---------------------------------------------------------------------------
# EnvironmentalData  (optional — temperature / humidity per hive)
# ---------------------------------------------------------------------------
class EnvironmentalData(Base):
    __tablename__ = "environmental_data"

    env_record_id = Column(UUID(as_uuid=False),
                           primary_key=True, default=new_uuid)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    humidity = Column(Numeric(5, 2))
    temperature = Column(Numeric(5, 2))
    recorded_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", back_populates="env_records")


# ---------------------------------------------------------------------------
# FeatureVector  (171 extracted features — stored for traceability)
# mfcc_value stores all 80 MFCC features as JSON text
# The individual float columns store the summary features
# ---------------------------------------------------------------------------
class FeatureVector(Base):
    __tablename__ = "feature_vectors"

    feature_id = Column(UUID(as_uuid=False),
                        primary_key=True, default=new_uuid)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    audio_id = Column(UUID(as_uuid=False), ForeignKey(
        "audio_sources.audio_id"), nullable=False)
    mfcc_value = Column(Text)       # JSON array of all MFCC coefficients
    spectral_centroid = Column(Float)
    spectral_bandwidth = Column(Float)
    signal_energy = Column(Float)
    zero_crossing_rate = Column(Float)
    temperature_normalised = Column(Float)
    humidity_normalised = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    audio_source = relationship(
        "AudioSource", back_populates="feature_vectors")
    inference_result = relationship(
        "InferenceResult", back_populates="feature_vector", uselist=False)


# ---------------------------------------------------------------------------
# InferenceResult  (what the model classified the audio as)
# hive_state: active_colony | swarming | missing_queen |
#             queenbee_present | external_noise
# ---------------------------------------------------------------------------
class InferenceResult(Base):
    __tablename__ = "inference_results"

    inference_id = Column(UUID(as_uuid=False),
                          primary_key=True, default=new_uuid)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    feature_id = Column(UUID(as_uuid=False), ForeignKey(
        "feature_vectors.feature_id"), nullable=True)
    hive_state = Column(String(30), nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=False)
    inference_latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", back_populates="inference_results")
    feature_vector = relationship(
        "FeatureVector", back_populates="inference_result")
    alert = relationship("Alert", back_populates="inference", uselist=False)
    advisory = relationship(
        "Advisory", back_populates="inference", uselist=False)


# ---------------------------------------------------------------------------
# Alert  (raised when state is swarming or missing_queen)
# action_status: pending | acknowledged
# ---------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    inference_id = Column(UUID(as_uuid=False), ForeignKey(
        "inference_results.inference_id"), nullable=False)
    severity_level = Column(String(20), nullable=False)   # High | Medium | Low
    recommended_action = Column(Text)
    action_status = Column(String(20), default="pending")
    generated_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", back_populates="alerts")
    inference = relationship("InferenceResult", back_populates="alert")


# ---------------------------------------------------------------------------
# Advisory  (container for a set of recommended actions)
# advisory_type: Reactive | Preventive
# ---------------------------------------------------------------------------
class Advisory(Base):
    __tablename__ = "advisories"

    advisory_id = Column(UUID(as_uuid=False),
                         primary_key=True, default=new_uuid)
    inference_id = Column(UUID(as_uuid=False), ForeignKey(
        "inference_results.inference_id"), nullable=False)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    advisory_type = Column(String(30))

    hive = relationship("Hive", back_populates="advisories")
    inference = relationship("InferenceResult", back_populates="advisory")
    actions = relationship("AdvisoryAction", back_populates="advisory")


# ---------------------------------------------------------------------------
# AdvisoryAction  (individual checklist items inside an advisory)
# ---------------------------------------------------------------------------
class AdvisoryAction(Base):
    __tablename__ = "advisory_actions"

    action_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    advisory_id = Column(UUID(as_uuid=False), ForeignKey(
        "advisories.advisory_id"), nullable=False)
    action_description = Column(Text, nullable=False)
    priority_level = Column(String(20))   # High | Medium | Low
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    advisory = relationship("Advisory", back_populates="actions")


# ---------------------------------------------------------------------------
# ImageSpectrum  (spectrogram image generated from audio)
# ---------------------------------------------------------------------------
class ImageSpectrum(Base):
    __tablename__ = "image_spectra"

    image_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"), nullable=False)
    audio_id = Column(UUID(as_uuid=False), ForeignKey(
        "audio_sources.audio_id"), nullable=False)
    image_type = Column(String(50), default="mel_spectrogram")
    image_uri = Column(String(255))
    generated_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", back_populates="image_spectra")
    audio_source = relationship("AudioSource", back_populates="image_spectra")


# ---------------------------------------------------------------------------
# FarmerDataSource
# Records HOW each farmer's audio data reaches the system.
#
# source_type options:
#   'folder'     — farmer drops .wav files into a watched folder on this server
#   'postgresql' — farmer's own PostgreSQL database (future)
#   'http'       — farmer's HTTP API endpoint (future)
#   's3'         — cloud storage bucket (future)
#
# For the MVP we use 'folder'. The folder path is auto-created when a hive
# is registered: data_sources/{user_id}/{hive_id}/
# The background poller scans every active folder every 30 seconds.
# ---------------------------------------------------------------------------
class FarmerDataSource(Base):
    __tablename__ = "farmer_data_sources"

    source_id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    hive_id = Column(Integer, ForeignKey("hives.hive_id"),
                     nullable=False, unique=True)
    # folder | postgresql | http | s3
    source_type = Column(String(50), default="folder")
    # folder path or connection string
    source_path = Column(Text)
    # future: DB creds, API keys, etc.
    connection_config = Column(JSON)
    last_scanned_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    hive = relationship("Hive", backref="data_source", uselist=False)
    user = relationship("User", backref="data_sources")
