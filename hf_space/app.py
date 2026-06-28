"""
HuggingFace Gradio Space — Bee Audio Classifier

Supports three backends selected by the MODEL_TYPE Space secret (env var):

  MODEL_TYPE=gradient_boosting  (default)
      gradient_boosting_model.pkl + label_encoder.pkl
      171 hand-crafted MFCC/chroma/spectral features

  MODEL_TYPE=cnn
      best_cnn_model.pth  (BeeAudioCNN — custom 4-block CNN)
      128-mel-bin log-mel spectrogram, 3 s segment, normalised /255

  MODEL_TYPE=resnet
      best_resnet18.pth  (modified ResNet-18, 1-channel input)
      same spectrogram pre-processing as cnn

  MODEL_TYPE=ensemble
      ensemble_model.pth  (BeeAudioCNN + ResNet-18, soft-vote average)
      same spectrogram pre-processing as cnn

Set MODEL_TYPE in Space Settings → Variables and Secrets to switch models.

All variants expose the SAME /predict API endpoint and return:
  {"label": "...", "score": 0.XX, "all_scores": {...}}
so the FastAPI backend needs zero changes.
"""

import os

import gradio as gr
import joblib
import librosa
import numpy as np
import torch
import torch.nn as nn
from huggingface_hub import hf_hub_download
import torchvision.models as tv_models

# ---------------------------------------------------------------------------
# Configuration — must match training exactly
# ---------------------------------------------------------------------------
REPO_ID    = "DerrickLegacy256/bee-audio-classifier"
MODEL_TYPE = os.getenv("MODEL_TYPE", "gradient_boosting").lower().strip()

SAMPLE_RATE = 22050
DURATION    = 3                 # seconds — matches training (DURATION=3)
N_MELS      = 128
N_FFT       = 2048s
HOP_LENGTH  = 512
DEVICE      = torch.device("cpu")   # HF free-tier has no GPU

# Computed time frames for a 3-second clip at these settings
# librosa.feature.melspectrogram produces ceil(sr*dur / hop_length) frames
CNN_TIME_FRAMES = int(np.ceil(SAMPLE_RATE * DURATION / HOP_LENGTH))  # ~130


# ---------------------------------------------------------------------------
# Model architecture definitions (must match training code exactly)
# ---------------------------------------------------------------------------

class BeeAudioCNN(nn.Module):
    """
    4-block CNN with BatchNorm, ReLU, MaxPool, and dropout.
    Matches the BeeAudioCNN class in bee_swarm_and_absconment_final_cnn_v4.ipynb.
    """
    def __init__(self, num_classes: int, dropout_rate: float = 0.5):
        super().__init__()

        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.Conv2d(32, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True),
            nn.MaxPool2d(2), nn.Dropout(0.1),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True),
            nn.MaxPool2d(2), nn.Dropout(0.15),
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True),
            nn.MaxPool2d(2), nn.Dropout(0.2),
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)), nn.Dropout(0.25),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256, 512), nn.ReLU(inplace=True), nn.Dropout(dropout_rate),
            nn.Linear(512, 256), nn.ReLU(inplace=True), nn.Dropout(dropout_rate * 0.8),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        return self.classifier(x)


def _build_resnet18(num_classes: int) -> nn.Module:
    """
    ResNet-18 with 1-channel conv1 and custom head.
    Matches get_resnet18() in the training notebook.
    """
    resnet = tv_models.resnet18(weights=None)
    resnet.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
    num_ftrs = resnet.fc.in_features
    resnet.fc = nn.Sequential(nn.Dropout(0.4), nn.Linear(num_ftrs, num_classes))
    return resnet


# ---------------------------------------------------------------------------
# Load model(s) + encoder at Space startup
# ---------------------------------------------------------------------------
print(f"[startup] MODEL_TYPE = {MODEL_TYPE}")
print(f"[startup] Downloading files from {REPO_ID} ...")

_encoder_path = hf_hub_download(REPO_ID, "cnn_label_encoder.pkl")
_label_encoder = joblib.load(_encoder_path)
NUM_CLASSES = len(_label_encoder.classes_)
_TOP30_FEATURES = []  # only populated for gradient_boosting
print(f"[startup] Classes ({NUM_CLASSES}): {list(_label_encoder.classes_)}")

if MODEL_TYPE in ("cnn", "resnet", "ensemble"):
    # PyTorch paths
    if MODEL_TYPE == "cnn":
        _weights_path = hf_hub_download(REPO_ID, "best_cnn_model.pth")
        _model = BeeAudioCNN(NUM_CLASSES).to(DEVICE)
        _model.load_state_dict(torch.load(_weights_path, map_location=DEVICE, weights_only=True))
        _model.eval()
        print(f"[startup] BeeAudioCNN loaded from best_cnn_model.pth")

    elif MODEL_TYPE == "resnet":
        _weights_path = hf_hub_download(REPO_ID, "best_resnet18.pth")
        _model = _build_resnet18(NUM_CLASSES).to(DEVICE)
        _model.load_state_dict(torch.load(_weights_path, map_location=DEVICE, weights_only=True))
        _model.eval()
        print(f"[startup] ResNet-18 loaded from best_resnet18.pth")

    elif MODEL_TYPE == "ensemble":
        _ensemble_path = hf_hub_download(REPO_ID, "ensemble_model.pth")
        checkpoint = torch.load(_ensemble_path, map_location=DEVICE, weights_only=True)
        _cnn_model    = BeeAudioCNN(NUM_CLASSES).to(DEVICE)
        _resnet_model = _build_resnet18(NUM_CLASSES).to(DEVICE)
        _cnn_model.load_state_dict(checkpoint["custom_cnn_state"])
        _resnet_model.load_state_dict(checkpoint["resnet_state"])
        _cnn_model.eval()
        _resnet_model.eval()
        _model = (_cnn_model, _resnet_model)   # tuple for ensemble
        print(f"[startup] Ensemble (CNN + ResNet-18) loaded from ensemble_model.pth")

else:
    # Gradient Boosting (default)
    import sklearn  # noqa — validates scikit-learn is installed
    import json as _json
    _gb_encoder_path = hf_hub_download(REPO_ID, "label_encoder.pkl")
    _gb_model_path   = hf_hub_download(REPO_ID, "gradient_boosting_model.pkl")
    _top30_path      = hf_hub_download(REPO_ID, "top30_features.json")
    _model           = joblib.load(_gb_model_path)
    _label_encoder   = joblib.load(_gb_encoder_path)   # overwrite with GB encoder
    _TOP30_FEATURES  = _json.loads(open(_top30_path).read())
    NUM_CLASSES      = len(_label_encoder.classes_)
    print(f"[startup] Gradient Boosting model loaded (expects {len(_TOP30_FEATURES)} features).")
    print(f"[startup] Classes ({NUM_CLASSES}): {list(_label_encoder.classes_)}")


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def _load_audio(audio_path: str) -> np.ndarray:
    """Load audio, trim/pad to DURATION seconds at SAMPLE_RATE."""
    y, _ = librosa.load(audio_path, sr=SAMPLE_RATE, duration=DURATION)
    target_len = SAMPLE_RATE * DURATION
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]
    return y


def _extract_mel_spectrogram(y: np.ndarray) -> np.ndarray:
    """
    Build a log-mel spectrogram and normalise to [0, 1] using min-max scaling.
    Matches load_single_audio() in cell 38 of the training notebook:
        mel_spec_db = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-8)
    Returns shape (1, H, W) ready for PyTorch (C, H, W).
    """
    mel = librosa.feature.melspectrogram(
        y=y, sr=SAMPLE_RATE, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH
    )
    mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)

    # Min-max normalise to [0, 1] — matches training exactly
    mel_norm = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)

    # Pad / crop time axis to a fixed width
    if mel_norm.shape[1] < CNN_TIME_FRAMES:
        pad = CNN_TIME_FRAMES - mel_norm.shape[1]
        mel_norm = np.pad(mel_norm, ((0, 0), (0, pad)), constant_values=0.0)
    else:
        mel_norm = mel_norm[:, :CNN_TIME_FRAMES]

    return mel_norm[np.newaxis, :, :]   # (1, H, W)


def _extract_classical_features(y: np.ndarray) -> np.ndarray:
    """
    Extract the top-30 features the GB model was trained on, in the exact
    order stored in top30_features.json. Computes all 171 features first,
    then selects and reorders to match training.
    """
    sr = SAMPLE_RATE
    feats: dict = {}

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40, n_fft=N_FFT, hop_length=HOP_LENGTH)
    for i in range(40):
        feats[f"mfcc_{i}_mean"] = float(np.mean(mfcc[i]))
        feats[f"mfcc_{i}_std"]  = float(np.std(mfcc[i]))

    delta = librosa.feature.delta(mfcc)
    for i in range(40):
        feats[f"mfcc_delta_{i}_mean"] = float(np.mean(delta[i]))

    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH)
    for i in range(12):
        feats[f"chroma_{i}_mean"] = float(np.mean(chroma[i]))
        feats[f"chroma_{i}_std"]  = float(np.std(chroma[i]))

    mel    = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=HOP_LENGTH)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    feats["mel_mean"] = float(np.mean(mel_db));  feats["mel_std"]  = float(np.std(mel_db))
    feats["mel_max"]  = float(np.max(mel_db));   feats["mel_min"]  = float(np.min(mel_db))

    sc = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)
    feats["spectral_centroid_mean"] = float(np.mean(sc))
    feats["spectral_centroid_std"]  = float(np.std(sc))

    sb = librosa.feature.spectral_bandwidth(y=y, sr=sr, hop_length=HOP_LENGTH)
    feats["spectral_bandwidth_mean"] = float(np.mean(sb))
    feats["spectral_bandwidth_std"]  = float(np.std(sb))

    sr_f = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=HOP_LENGTH)
    feats["spectral_rolloff_mean"] = float(np.mean(sr_f))
    feats["spectral_rolloff_std"]  = float(np.std(sr_f))

    contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=HOP_LENGTH)
    for i in range(contrast.shape[0]):
        feats[f"spectral_contrast_{i}_mean"] = float(np.mean(contrast[i]))

    zcr = librosa.feature.zero_crossing_rate(y, hop_length=HOP_LENGTH)
    feats["zcr_mean"] = float(np.mean(zcr));  feats["zcr_std"] = float(np.std(zcr))

    rms = librosa.feature.rms(y=y, hop_length=HOP_LENGTH)
    feats["rms_mean"] = float(np.mean(rms));  feats["rms_std"] = float(np.std(rms))

    harmonic = librosa.effects.harmonic(y)
    tonnetz  = librosa.feature.tonnetz(y=harmonic, sr=sr)
    for i in range(6):
        feats[f"tonnetz_{i}_mean"] = float(np.mean(tonnetz[i]))

    # Select only the top-30 features the model was trained on, in training order
    return np.array([feats[f] for f in _TOP30_FEATURES]).reshape(1, -1)


def _pytorch_inference(model_or_tuple, tensor: torch.Tensor) -> np.ndarray:
    """Run PyTorch inference, return softmax probabilities as numpy array."""
    with torch.no_grad():
        if isinstance(model_or_tuple, tuple):
            # Ensemble: average softmax from both models
            cnn_m, res_m = model_or_tuple
            p_cnn    = torch.softmax(cnn_m(tensor), dim=1)
            p_resnet = torch.softmax(res_m(tensor), dim=1)
            proba    = ((p_cnn + p_resnet) / 2.0).cpu().numpy()[0]
        else:
            logits = model_or_tuple(tensor)
            proba  = torch.softmax(logits, dim=1).cpu().numpy()[0]
    return proba


# ---------------------------------------------------------------------------
# Prediction endpoint
# ---------------------------------------------------------------------------

def predict(audio_path: str) -> dict:
    """
    Accept any audio file, classify it, return:
    {"label": "...", "score": 0.XX, "all_scores": {"class": score, ...}}
    """
    y = _load_audio(audio_path)

    if MODEL_TYPE in ("cnn", "resnet", "ensemble"):
        mel = _extract_mel_spectrogram(y)                         # (1, H, W)
        tensor = torch.tensor(mel, dtype=torch.float32).unsqueeze(0).to(DEVICE)  # (1,1,H,W)
        proba  = _pytorch_inference(_model, tensor)

        class_index = int(np.argmax(proba))
        label       = str(_label_encoder.classes_[class_index])
        confidence  = float(proba[class_index])
        all_scores  = {str(cls): float(p) for cls, p in zip(_label_encoder.classes_, proba)}

    else:
        # Gradient Boosting
        features    = _extract_classical_features(y)
        class_index = _model.predict(features)[0]
        proba       = _model.predict_proba(features)[0]
        label       = str(_label_encoder.classes_[class_index])
        confidence  = float(proba[class_index])
        all_scores  = {str(cls): float(p) for cls, p in zip(_label_encoder.classes_, proba)}

    return {"label": label, "score": confidence, "all_scores": all_scores}


# ---------------------------------------------------------------------------
# Gradio interface
# ---------------------------------------------------------------------------
_model_display = MODEL_TYPE.replace("_", " ").title()

iface = gr.Interface(
    fn=predict,
    inputs=gr.Audio(type="filepath", label="Hive audio recording (.wav/.mp3)"),
    outputs=gr.JSON(label="Classification result"),
    title=f"Bee Audio Classifier — {_model_display}",
    description=(
        f"<b>Active model:</b> {MODEL_TYPE}  "
        f"<b>Classes:</b> active_colony | external_noise | inactive_hive | "
        f"pests | quacking_queen_bee | queenbee_absent | swarming<br>"
        f"Change model via the <code>MODEL_TYPE</code> Space secret."
    ),
    api_name="predict",
)

iface.launch()
