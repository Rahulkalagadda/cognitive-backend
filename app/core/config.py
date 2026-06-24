import json
import os
from typing import List, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cognitive Assessment Platform (CAP) API"
    VERSION: str = "2.5.0-LTS"
    ENV: str = "development"

    # Database
    DATABASE_URL: str

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # OTP
    OTP_SECRET_KEY: str

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # CORS
    # Set in Railway as:
    #   BACKEND_CORS_ORIGINS=https://cognitive-function-by-drm.vercel.app
    # or comma-separated:
    #   BACKEND_CORS_ORIGINS=https://cognitive-function-by-drm.vercel.app,https://other.example.com
    # or JSON array:
    #   BACKEND_CORS_ORIGINS=["https://cognitive-function-by-drm.vercel.app"]
    #
    # WARNING: Do NOT use "*" (wildcard) together with allow_credentials=True.
    # The browser will reject the response. Always list explicit origins in
    # production.
    BACKEND_CORS_ORIGINS: Any = ["https://cognitive-function-by-drm.vercel.app"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if not v:
            # Default to the Vercel frontend — never return bare "*" because
            # allow_credentials=True + wildcard origin is rejected by browsers.
            return ["https://cognitive-function-by-drm.vercel.app"]
        if isinstance(v, list):
            return [str(origin).strip().rstrip("/") for origin in v if str(origin).strip()]
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                # JSON array: '["https://a.com","https://b.com"]'
                parsed = json.loads(stripped)
                return [str(o).strip().rstrip("/") for o in parsed if str(o).strip()]
            # Comma-separated: "https://a.com,https://b.com"
            return [o.strip().rstrip("/") for o in stripped.split(",") if o.strip()]
        raise ValueError(f"Invalid BACKEND_CORS_ORIGINS value: {v!r}")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
