"""
Shared audio processing logic.

Called by:
  - api/routers/audio.py      (manual farmer upload)
  - api/poller.process_pending_sources()  (automated poller job)

Flow:
  1. Mark AudioSource as "processing"
  2. POST audio bytes to HuggingFace Inference API
  3. Save InferenceResult
  4. Generate alert + advisory if state is dangerous
  5. Mark AudioSource as "processed" (or "failed" on error)

Note: Environmental data is recorded when the audio source is first registered,
not during processing, to ensure temperature/humidity match the exact audio capture time.
"""

import traceback

from sqlalchemy.orm import Session

from api import advisory_new as advisory_module
from api.database import SessionLocal
from api.inference_engine import predict_from_bytes
from api.models import AudioSource, Hive, InferenceResult
from api.system_logger import exc_details, log


# Mapping from ML model labels to database hive_state vocabulary
# Database expects: normal | pre_swarm | swarm | abscondment | missing_queen |
#                   queenbee_present | pest_infested | external_noise | uncertain
LABEL_TO_HIVE_STATE = {
    # --- original 5-class GB model labels ---
    "swarming": "swarm",
    "swarm": "swarm",
    "pre-swarming": "pre_swarm",
    "pre_swarm": "pre_swarm",
    "normal": "normal",
    "healthy": "normal",
    "abscondment": "abscondment",
    "absconding": "abscondment",
    "missing_queen": "missing_queen",
    "queenless": "missing_queen",
    "queenbee_present": "queenbee_present",
    "queen_present": "queenbee_present",
    "pest_infested": "pest_infested",
    "pest": "pest_infested",
    "external_noise": "external_noise",
    "noise": "external_noise",
    "uncertain": "uncertain",
    "unknown": "uncertain",

    # --- 7-class CNN / ResNet / Ensemble model labels ---
    "active_colony": "normal",           # healthy active colony
    "inactive_hive": "abscondment",      # hive has gone quiet / absconded
    "pests": "pest_infested",            # pest presence detected
    "quacking_queen_bee": "queenbee_present",  # virgin/quacking queen heard
    "queenbee_absent": "missing_queen",  # no queen detected
    # "swarming" and "external_noise" already covered above
}


def normalize_hive_state(model_label: str) -> str:
    """
    Normalize the ML model's label to match the database hive_state vocabulary.
    
    Args:
        model_label: Raw label from the ML model (e.g., "swarming")
    
    Returns:
        Normalized hive_state (e.g., "swarm")
    """
    normalized = model_label.lower().strip().replace(" ", "_").replace("-", "_")
    return LABEL_TO_HIVE_STATE.get(normalized, "uncertain")


def process_audio_file(audio_id: str, audio_bytes: bytes, hive_id: str) -> None:
    """
    Full pipeline for one audio file.

    Opens its own DB session — safe to call from background tasks,
    the poller thread, or anywhere outside a FastAPI request context.
    """
    db: Session = SessionLocal()
    try:
        audio_record = db.query(AudioSource).filter(AudioSource.audio_id == audio_id).first()
        if not audio_record:
            return

        audio_record.status = "processing"
        db.commit()

        # --- Send to HuggingFace Inference API ---
        result = predict_from_bytes(audio_bytes)

        # Normalize the model's label to match database vocabulary
        hive_state = normalize_hive_state(result.label)

        # Sort all scores descending for top_predictions
        sorted_predictions = sorted(
            result.all_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        prediction_details = {
            "predicted_class": hive_state,
            "confidence": float(result.confidence),
            # Top-3 with DB-normalised class names (what the app uses for alerts/display)
            "top_predictions": [
                {
                    "class": normalize_hive_state(class_name),
                    "confidence": float(conf),
                }
                for class_name, conf in sorted_predictions[:3]
            ],
            # Full scores from the model — raw labels preserved so nothing is lost
            "all_scores": {
                class_name: float(conf)
                for class_name, conf in sorted_predictions
            },
        }

        # --- Inference result ---
        inference = InferenceResult(
            hive_id              = hive_id,
            audio_id             = audio_id,  # Link to the audio source
            hive_state           = hive_state,
            confidence_score     = result.confidence,
            prediction_details   = prediction_details,  # Store full prediction data
            inference_latency_ms = result.latency_ms,
        )
        db.add(inference)
        db.flush()

        # --- Alert + advisory if dangerous state ---
        hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
        advisory_module.generate(inference, hive, db)

        # --- Keep hive.current_state in sync with the latest inference ---
        if hive:
            hive.current_state = hive_state

        audio_record.status = "processed"

        log(db, "info", "inference",
            f"Classified as {hive_state} ({result.confidence:.2%}) in {result.latency_ms}ms",
            hive_id=hive_id, audio_id=audio_id,
            details={
                "model_label": result.label,
                "hive_state": hive_state,
                "confidence": result.confidence,
                "latency_ms": result.latency_ms
            })

        db.commit()

    except Exception as exc:
        db.rollback()
        try:
            record = db.query(AudioSource).filter(AudioSource.audio_id == audio_id).first()
            if record:
                record.status = "failed"
                log(db, "error", "inference",
                    f"Processing failed: {type(exc).__name__}: {exc}",
                    hive_id=hive_id, audio_id=audio_id,
                    details=exc_details(exc))
                db.commit()
        except Exception:
            pass
        traceback.print_exc()
    finally:
        db.close()
