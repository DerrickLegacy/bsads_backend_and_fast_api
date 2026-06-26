"""
Uploads Space files (app.py, requirements.txt) and local model files
(.pth CNN models) to the HuggingFace repo.

Run with:
    venv/bin/python hf_space/upload_space.py
"""
import os
from pathlib import Path
from huggingface_hub import HfApi

SPACE_ID  = "DerrickLegacy256/bee-audio-classifier"
MODEL_ID  = "DerrickLegacy256/bee-audio-classifier"   # same repo — it's a model repo + Space
HF_TOKEN  = os.environ.get("HF_WRITE_TOKEN") or os.environ.get("HF_TOKEN")

if not HF_TOKEN:
    raise SystemExit("❌  Set HF_WRITE_TOKEN or HF_TOKEN in your environment")

SPACE_DIR      = Path(__file__).parent                          # hf_space/
PROJECT_ROOT   = SPACE_DIR.parent                               # bsads_backend_and_fast_api/
CLASSIFIER_ROOT = PROJECT_ROOT.parent / "bee_swarming_audio_classifer"
LOCAL_CNN_DIR  = CLASSIFIER_ROOT / "models" / "cnn"
LOCAL_ML_DIR   = CLASSIFIER_ROOT / "models" / "classicalMl"

api = HfApi(token=HF_TOKEN)

# ---------------------------------------------------------------------------
# 1. Upload Space files (app.py + requirements.txt) to the Gradio Space repo
# ---------------------------------------------------------------------------
print("=" * 60)
print("Step 1 — Uploading Space files")
print("=" * 60)

space_files = ["app.py", "requirements.txt"]
for fname in space_files:
    local = SPACE_DIR / fname
    if not local.exists():
        raise SystemExit(f"❌  {local} not found")
    print(f"⬆️  {fname} → Space {SPACE_ID} ...")
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=fname,
        repo_id=SPACE_ID,
        repo_type="space",
        commit_message=f"Update {fname}: PyTorch CNN + GB dual-model support",
    )
    print(f"   ✓ done")

# ---------------------------------------------------------------------------
# 2. Upload CNN .pth model files to the model repo
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("Step 2 — Uploading CNN model files to model repo")
print("=" * 60)

cnn_files = [
    ("best_cnn_model.pth",     LOCAL_CNN_DIR),
    ("bee_cnn_classifier.pth", LOCAL_CNN_DIR),
    ("best_resnet18.pth",      LOCAL_CNN_DIR),
    ("ensemble_model.pth",     LOCAL_CNN_DIR),
    ("cnn_label_encoder.pkl",  LOCAL_CNN_DIR),
    ("class_names.txt",        LOCAL_CNN_DIR),
]

for fname, src_dir in cnn_files:
    local = src_dir / fname
    if not local.exists():
        print(f"   ⚠️  {fname} not found in {src_dir} — skipping")
        continue
    size_mb = local.stat().st_size / 1024 / 1024
    print(f"⬆️  {fname} ({size_mb:.1f} MB) → model repo {MODEL_ID} ...")
    api.upload_file(
        path_or_fileobj=str(local),
        path_in_repo=fname,
        repo_id=MODEL_ID,
        repo_type="model",
        commit_message=f"Upload {fname} (PyTorch CNN)",
    )
    print(f"   ✓ done")

print()
print("=" * 60)
print("✅  All uploads complete!")
print("=" * 60)
print()
print(f"Space:      https://huggingface.co/spaces/{SPACE_ID}")
print(f"Model repo: https://huggingface.co/{MODEL_ID}")
print()
print("To activate the CNN model, add this Secret in the Space settings:")
print("   Name:  MODEL_TYPE")
print("   Value: cnn")
print()
print("Other valid values: resnet | ensemble | gradient_boosting (default)")
