"""
Inference engine — sends raw audio bytes to the HuggingFace Gradio Space
and returns the top classification result.

No model is downloaded or run locally.  All feature extraction and
inference happen inside the HF Space on HuggingFace's servers.
"""

import os
import tempfile
import time
from dataclasses import dataclass

import httpx
from gradio_client import Client, handle_file

from api.config import settings

# Timeout covers upload + inference — configurable via INFERENCE_TIMEOUT_SECONDS in .env
def _httpx_kwargs() -> dict:
    return {"timeout": httpx.Timeout(float(settings.inference_timeout_seconds))}


@dataclass
class PredictionResult:
    label: str        # e.g. "swarming"
    confidence: float  # 0.0 – 1.0
    latency_ms: int   # round-trip time to HF Space
    all_scores: dict  # All class predictions with confidence scores


_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.hf_space_name, httpx_kwargs=_httpx_kwargs())
    return _client


def predict_from_bytes(audio_bytes: bytes) -> PredictionResult:
    """
    Write audio bytes to a temp file, POST it to the HF Space /predict
    endpoint, and return the top classification result.

    The temp file is deleted immediately after the call.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        t0 = time.perf_counter()
        result = _get_client().predict(handle_file(tmp_path), api_name="/predict")
        latency_ms = int((time.perf_counter() - t0) * 1000)

        # result is a dict: {"label": "...", "score": 0.XX, "all_scores": {...}}
        return PredictionResult(
            label=result["label"],
            confidence=float(result["score"]),
            latency_ms=latency_ms,
            all_scores=result.get("all_scores", {}),  # Capture all prediction scores
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
