"""
HuggingFace Gradio Space — Bee Audio Classifier

This Space loads the trained gradient-boosting model from the HF Hub repo
and exposes a single /predict API endpoint that accepts a WAV audio file
and returns the hive state classification.

Your FastAPI service POSTs audio bytes here — the model never touches
the FastAPI server.

Deploy this file (plus requirements.txt) as a new HuggingFace Space of
type "Gradio".  Set HF_TOKEN in the Space secrets if the model repo is private.
"""

import json

import gradio as gr
import joblib
import librosa
import numpy as np
from huggingface_hub import hf_hub_download

# ---------------------------------------------------------------------------
# Load model + encoder at Space startup (runs on HF's servers, not yours)
# ---------------------------------------------------------------------------
REPO_ID = "DerrickLegacy256/bee_swarming_and_absconment"

_model_path   = hf_hub_download(REPO_ID, "gradient_boosting_model.pkl")
_encoder_path = hf_hub_download(REPO_ID, "label_encoder.pkl")
_model         = joblib.load(_model_path)
_label_encoder = joblib.load(_encoder_path)

print(f"Model loaded from {REPO_ID}")


# ---------------------------------------------------------------------------
# Feature extraction — 171 features, identical to the training pipeline
# ---------------------------------------------------------------------------
def _extract_features(y: np.ndarray, sr: int) -> np.ndarray:
    feats: dict = {}

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40, n_fft=2048, hop_length=512)
    for i in range(40):
        feats[f"mfcc_{i}_mean"] = float(np.mean(mfcc[i]))
        feats[f"mfcc_{i}_std"]  = float(np.std(mfcc[i]))

    delta = librosa.feature.delta(mfcc)
    for i in range(40):
        feats[f"mfcc_delta_{i}_mean"] = float(np.mean(delta[i]))

    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=2048, hop_length=512)
    for i in range(12):
        feats[f"chroma_{i}_mean"] = float(np.mean(chroma[i]))
        feats[f"chroma_{i}_std"]  = float(np.std(chroma[i]))

    mel    = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=512)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    feats["mel_mean"] = float(np.mean(mel_db))
    feats["mel_std"]  = float(np.std(mel_db))
    feats["mel_max"]  = float(np.max(mel_db))
    feats["mel_min"]  = float(np.min(mel_db))

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

    zcr = librosa.feature.zero_crossing_rate(y, hop_length=512)
    feats["zcr_mean"] = float(np.mean(zcr))
    feats["zcr_std"]  = float(np.std(zcr))

    rms = librosa.feature.rms(y=y, hop_length=512)
    feats["rms_mean"] = float(np.mean(rms))
    feats["rms_std"]  = float(np.std(rms))

    harmonic = librosa.effects.harmonic(y)
    tonnetz  = librosa.feature.tonnetz(y=harmonic, sr=sr)
    for i in range(6):
        feats[f"tonnetz_{i}_mean"] = float(np.mean(tonnetz[i]))

    return np.array(list(feats.values())).reshape(1, -1)


# ---------------------------------------------------------------------------
# Prediction function — called by the Gradio interface
# ---------------------------------------------------------------------------
def predict(audio_path: str) -> dict:
    """
    Accept a WAV file path, run the full classification pipeline,
    return {"label": "...", "score": 0.XX, "all_scores": {...}}.
    """
    y, sr = librosa.load(audio_path, sr=22050)
    y = y[:int(5.0 * sr)]          # first 5 seconds only (matches training)

    vector      = _extract_features(y, sr)
    class_index = _model.predict(vector)[0]
    proba       = _model.predict_proba(vector)[0]

    label      = _label_encoder.classes_[class_index]
    confidence = float(proba[class_index])
    all_scores = {
        cls: float(p)
        for cls, p in zip(_label_encoder.classes_, proba)
    }

    return {"label": label, "score": confidence, "all_scores": all_scores}


# ---------------------------------------------------------------------------
# Gradio interface — exposes /api/predict for programmatic access
# ---------------------------------------------------------------------------
iface = gr.Interface(
    fn=predict,
    inputs=gr.Audio(type="filepath", label="Hive audio recording"),
    outputs=gr.JSON(label="Classification result"),
    title="Bee Swarming & Abscondment Audio Classifier",
    description=(
        "Upload a WAV recording from a hive. "
        "Returns: active_colony | swarming | missing_queen | queenbee_present | external_noise"
    ),
    api_name="predict",
)

iface.launch()
