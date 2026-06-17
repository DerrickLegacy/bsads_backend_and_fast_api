from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str                      # required — no insecure default
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24   # 1 day
    upload_dir: str = "uploads"

    # HuggingFace inference space — audio bytes are sent here for classification
    hf_space_name: str                   # required — set HF_SPACE_NAME in .env
    hf_token: str = ""                   # set HF_TOKEN in .env if the Space is private
    hf_write_token: str = ""             # optional — only needed for CI/CD model pushes
    hf_model_id: str = ""               # HF model repo (informational / CI use)

    # Background poller timing
    poll_interval_seconds: int = 60      # how often discovery + inference jobs run (increased to 60s)
    poll_offset_seconds: int = 15        # offset so inference runs after discovery
    recovery_interval_minutes: int = 5   # how often to check for stuck records

    # HuggingFace inference timeout
    inference_timeout_seconds: int = 240

    # Database reset on startup (DEVELOPMENT ONLY - deletes all data!)
    reset_database: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Absolute path to the project root (one level above api/)
ROOT = Path(__file__).resolve().parent.parent
