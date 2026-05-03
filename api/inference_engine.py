"""
Inference engine — loads the trained model once at startup and exposes
a single predict() function used by the audio upload router.

Feature extraction replicates the exact 171-feature pipeline from the
training notebooks so the model receives the same input shape it was
trained on.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path

import joblib
import librosa
import numpy as np
from huggingface_hub import hf_hub_download

from api.config import settings


@dataclass
class PredictionResult:
    label: str           # e.g. "swarming"
    confidence: float    # 0.0 – 1.0
    latency_ms: int      # how long inference took
    mfcc_json: str       # JSON string of MFCC coefficients (for feature_vector table)
    spectral_centroid: float
    spectral_bandwidth: float
    signal_energy: float
    zero_crossing_rate: float


# ---------------------------------------------------------------------------
# Download model + encoder from HuggingFace Hub once at startup.
# hf_hub_download caches files in ~/.cache/huggingface/hub/ so after the
# first run this is instant — no repeated downloads.
# ---------------------------------------------------------------------------
_token = settings.hf_token or None

_model = joblib.load(
    hf_hub_download(settings.hf_repo_id, "gradient_boosting_model.pkl", token=_token)
)
_label_encoder = joblib.load(
    hf_hub_download(settings.hf_repo_id, "label_encoder.pkl", token=_token)
)

print(f"✓ Model loaded from HuggingFace: {settings.hf_repo_id}")


# ---------------------------------------------------------------------------
# Feature extraction  — 171 features, matching the training pipeline
# ---------------------------------------------------------------------------
def _extract_features(y: np.ndarray, sr: int) -> tuple[np.ndarray, dict]:
    """
    Returns:
        vector  — shape (1, 171) ready for model.predict()
        summary — key feature values stored in feature_vector table
    """
    feats: dict = {}

    # 40 MFCCs × (mean + std) = 80 features
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40, n_fft=2048, hop_length=512)
    for i in range(40):
        feats[f"mfcc_{i}_mean"] = float(np.mean(mfcc[i]))
        feats[f"mfcc_{i}_std"]  = float(np.std(mfcc[i]))

    # 40 delta-MFCCs × mean = 40 features
    delta = librosa.feature.delta(mfcc)
    for i in range(40):
        feats[f"mfcc_delta_{i}_mean"] = float(np.mean(delta[i]))

    # 12 Chroma × (mean + std) = 24 features
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=2048, hop_length=512)
    for i in range(12):
        feats[f"chroma_{i}_mean"] = float(np.mean(chroma[i]))
        feats[f"chroma_{i}_std"]  = float(np.std(chroma[i]))

    # Mel spectrogram stats = 4 features
    mel = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=512)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    feats["mel_mean"] = float(np.mean(mel_db))
    feats["mel_std"]  = float(np.std(mel_db))
    feats["mel_max"]  = float(np.max(mel_db))
    feats["mel_min"]  = float(np.min(mel_db))

    # Spectral features = 2+2+2+7 = 13 features
    sc = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)
    feats["spectral_centroid_mean"] = float(np.mean(sc))
    feats["spectral_centroid_std"]  = float(np.std(sc))

    sb = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=512)
    feats["spectral_bandwidth_mean"] = float(np.mean(sb))
    feats["spectral_bandwidth_std"]  = float(np.std(sb))

    sr_f = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=512)
    feats["spectral_rolloff_mean"] = float(np.mean(sr_f))
    feats["spectral_rolloff_std"]  = float(np.std(sr_f))

    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=512)
    for i in range(contrast.shape[0]):
        feats[f"spectral_contrast_{i}_mean"] = float(np.mean(contrast[i]))

    # Zero crossing rate = 2 features
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=512)
    feats["zcr_mean"] = float(np.mean(zcr))
    feats["zcr_std"]  = float(np.std(zcr))

    # RMS energy = 2 features
    rms = librosa.feature.rms(y=y, hop_length=512)
    feats["rms_mean"] = float(np.mean(rms))
    feats["rms_std"]  = float(np.std(rms))

    # Tonnetz = 6 features
    harmonic = librosa.effects.harmonic(y)
    tonnetz = librosa.feature.tonnetz(y=harmonic, sr=sr)
    for i in range(6):
        feats[f"tonnetz_{i}_mean"] = float(np.mean(tonnetz[i]))

    vector = np.array(list(feats.values())).reshape(1, -1)

    # Summary fields stored in feature_vector table
    mfcc_coeffs = [feats[f"mfcc_{i}_mean"] for i in range(40)]
    summary = {
        "mfcc_json":          json.dumps(mfcc_coeffs),
        "spectral_centroid":  feats["spectral_centroid_mean"],
        "spectral_bandwidth": feats["spectral_bandwidth_mean"],
        "signal_energy":      feats["rms_mean"],
        "zero_crossing_rate": feats["zcr_mean"],
    }

    return vector, summary


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def predict(file_path: str | Path, sample_rate: int = 22050) -> PredictionResult:
    """
    Load an audio file, extract features, run the model, return a result.

    Parameters
    ----------
    file_path   : local path to the .wav file
    sample_rate : target sample rate (must match training — 22050 Hz)
    """
    y, sr = librosa.load(str(file_path), sr=sample_rate)

    # Use first 5 seconds only (matching training segment length)
    segment_samples = int(5.0 * sr)
    y = y[:segment_samples]

    vector, summary = _extract_features(y, sr)

    t0 = time.perf_counter()
    class_index = _model.predict(vector)[0]
    proba = _model.predict_proba(vector)[0]
    latency_ms = int((time.perf_counter() - t0) * 1000)

    label = _label_encoder.classes_[class_index]
    confidence = float(proba[class_index])

    return PredictionResult(
        label=label,
        confidence=confidence,
        latency_ms=latency_ms,
        mfcc_json=summary["mfcc_json"],
        spectral_centroid=summary["spectral_centroid"],
        spectral_bandwidth=summary["spectral_bandwidth"],
        signal_energy=summary["signal_energy"],
        zero_crossing_rate=summary["zero_crossing_rate"],
    )
