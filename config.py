"""Application-wide settings loaded from environment variables and .env file."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATA_DIR: Path = Path("./data")
    DB_PATH: Path = Path("./trial_transparency.db")
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SAMPLE_SIZE: int = 500
    LOG_LEVEL: str = "INFO"


settings = Settings()
