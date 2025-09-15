# google_scholar_02/settings.py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    Defines the expected keys for deployment (project, location, bucket, API keys).
    Unknown extra variables are ignored.
    """

    serpapi_api_key: Optional[str] = None
    google_genai_use_vertexai: bool = True
    staging_bucket: Optional[str] = None
    google_cloud_location: Optional[str] = None
    google_cloud_project: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown environment vars
    )

__all__ = ["Settings"]

# Default instance for project-wide use
settings = Settings()