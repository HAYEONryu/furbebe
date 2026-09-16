"""Environment configuration. Credentials never appear in validation messages."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ROOT = Path(__file__).resolve().parents[3]


class ConfigurationError(RuntimeError):
    """A safe startup failure, without values from environment variables."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
        hide_input_in_errors=True,
        frozen=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    frontend_origin: str = "http://localhost:5173"
    db_connect_timeout: int = Field(default=5, ge=1, le=30)
    db_statement_timeout_ms: int = Field(default=5000, ge=100, le=30000)

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value):
        value = value.get_secret_value() if isinstance(value, SecretStr) else value
        if value is None or isinstance(value, str) and not value.strip():
            return None
        try:
            url = make_url(value)
            if url.drivername not in {"postgresql", "postgresql+psycopg"}:
                raise ValueError
            if not url.host or not url.database:
                raise ValueError
            # Force psycopg 3 even for standard PostgreSQL URLs; keep TLS query options.
            return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
        except (ArgumentError, TypeError, ValueError):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL with host and database"
            ) from None

    @field_validator("frontend_origin")
    @classmethod
    def validate_origins(cls, value):
        origins = list(dict.fromkeys(part.strip().rstrip("/") for part in value.split(",")))
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                port = parsed.port
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                    or "*" in origin
                    or any(char.isspace() for char in origin)
                    or port == 0
                ):
                    raise ValueError
            except ValueError:
                raise ValueError("FRONTEND_ORIGIN must contain exact HTTP(S) origins") from None
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_production(self):
        if self.app_env == "production":
            if self.database_url is None:
                raise ValueError("DATABASE_URL is required in production")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production FRONTEND_ORIGIN must use HTTPS")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return self.frontend_origin.split(",")


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError:
        raise ConfigurationError(
            "Invalid backend configuration; check environment settings"
        ) from None
