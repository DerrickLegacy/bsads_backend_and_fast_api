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
"""

import traceback

from sqlalchemy.orm import Session

from api import advisory as advisory_module
from api.database import SessionLocal
from api.inference_engine import predict_from_bytes
from api.models import AudioSource, Hive, InferenceResult
from api.system_logger import exc_details, log


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

        # --- Inference result ---
        inference = InferenceResult(
            hive_id              = hive_id,
            hive_state           = result.label,
            confidence_score     = result.confidence,
            inference_latency_ms = result.latency_ms,
        )
        db.add(inference)
        db.flush()

        # --- Alert + advisory if dangerous state ---
        hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
        advisory_module.generate(inference, hive, db)

        audio_record.status = "processed"

        log(db, "info", "inference",
            f"Classified as {result.label} ({result.confidence:.2%}) in {result.latency_ms}ms",
            hive_id=hive_id, audio_id=audio_id,
            details={"hive_state": result.label, "confidence": result.confidence, "latency_ms": result.latency_ms})

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
