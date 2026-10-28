"""Validated configuration loaded from environment variables or a local .env."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PATCHPILOT_", env_file=".env", env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = Field(default="patchpilot-api", min_length=1)
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", min_length=1, max_length=120)
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3000", "http://127.0.0.1:3000",
    ], max_length=10)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in ("http", "https") or not parsed.hostname
                    or "*" in origin or parsed.username is not None or parsed.password is not None
                    or parsed.path or parsed.query or parsed.fragment):
                raise ValueError("CORS entries must be explicit HTTP(S) origins without paths")
            _ = parsed.port  # Validate port syntax/range too.
        return origins
