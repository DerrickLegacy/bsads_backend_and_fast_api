from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    upload_dir: str = "uploads"

    # HuggingFace Hub — model is downloaded at startup and cached locally
    hf_repo_id: str = "DerrickLegacy256/bee-audio-classifier"
    hf_token: str = ""   # optional for public repos; set HF_TOKEN= in .env for private

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Absolute path to the project root (one level above api/)
ROOT = Path(__file__).resolve().parent.parent
