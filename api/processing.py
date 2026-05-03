"""
Shared audio processing logic.

Called by:
  - api/routers/audio.py  (when a farmer uploads a file manually)
  - api/poller.py         (when the folder watcher finds a new file)

Both paths do the same thing: extract features → run model → save results.
"""

from pathlib import Path

from sqlalchemy.orm import Session

from api import advisory as advisory_module
from api.database import SessionLocal
from api.inference_engine import predict
from api.models import AudioSource, FeatureVector, Hive, InferenceResult


def process_audio_file(audio_id: str, file_path: Path, hive_id: int) -> None:
    """
    Full pipeline for one audio file:
      1. Extract 171 features
      2. Run Gradient Boosting model
      3. Save feature_vector + inference_result rows
      4. Generate alert + advisory if state is dangerous
      5. Mark audio_source as processed (or failed on error)

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

        # --- Run inference ---
        result = predict(file_path)

        # --- Feature vector (for traceability / reproducibility) ---
        fv = FeatureVector(
            hive_id            = hive_id,
            audio_id           = audio_id,
            mfcc_value         = result.mfcc_json,
            spectral_centroid  = result.spectral_centroid,
            spectral_bandwidth = result.spectral_bandwidth,
            signal_energy      = result.signal_energy,
            zero_crossing_rate = result.zero_crossing_rate,
        )
        db.add(fv)
        db.flush()

        # --- Inference result ---
        inference = InferenceResult(
            hive_id              = hive_id,
            feature_id           = fv.feature_id,
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

        print(f"[INFERENCE] hive={hive_id} file={Path(file_path).name} "
              f"→ {result.label} ({result.confidence:.2%}) in {result.latency_ms}ms")

    except Exception as exc:
        db.rollback()
        try:
            record = db.query(AudioSource).filter(AudioSource.audio_id == audio_id).first()
            if record:
                record.status = "failed"
                db.commit()
        except Exception:
            pass
        print(f"[ERROR] processing failed for audio {audio_id}: {exc}")
    finally:
        db.close()
