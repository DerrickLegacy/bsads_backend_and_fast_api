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


def process_audio_file(audio_id: str, audio_bytes: bytes, hive_id: int) -> None:
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

        # --- Alert + advisory if swarming or missing_queen ---
        hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
        advisory_module.generate(inference, hive, db)

        audio_record.status = "processed"
        db.commit()

        print(
            f"[INFERENCE] hive={hive_id} audio={audio_id} "
            f"→ {result.label} ({result.confidence:.2%}) in {result.latency_ms}ms"
        )

    except Exception as exc:
        db.rollback()
        try:
            record = db.query(AudioSource).filter(AudioSource.audio_id == audio_id).first()
            if record:
                record.status = "failed"
                db.commit()
        except Exception:
            pass
        print(f"[ERROR] processing failed for audio {audio_id}: {type(exc).__name__}: {exc}")
        traceback.print_exc()
    finally:
        db.close()
