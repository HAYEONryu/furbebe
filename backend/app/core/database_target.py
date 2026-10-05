"""Explicit database selection for operational commands; never infer a remote target."""

import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from .config import ROOT, ConfigurationError, Settings, get_settings

TARGET_ENV = "FURBEBE_DATABASE_TARGET"
CONNECTION_OVERRIDES = {"host", "hostaddr", "port", "dbname", "service", "servicefile"}


def _get_supabase_database_settings(stage: str, env_file: Path | None = None) -> Settings:
    """Bind a named DB credential to an independently configured project."""
    try:
        values = dotenv_values(env_file or ROOT / ".env", interpolate=False, encoding="utf-8-sig")

        def value(key):
            return os.environ.get(key, values.get(key))

        expected_env = "production" if stage == "prod" else "development"
        allowed_env = ("production",) if stage == "prod" else (None, "", "development")
        if value("APP_ENV") not in allowed_env:
            raise ValueError
        url = make_url(value(f"DATABASE_URL_{stage}") or "")
        project = urlsplit(value(f"SUPABASE_URL_{stage}") or "")
        project_host = project.hostname or ""
        if (
            project.scheme != "https"
            or not re.fullmatch(r"[a-z0-9]+\.supabase\.co", project_host)
            or project.username
            or project.password
            or project.port not in (None, 443)
            or project.path not in ("", "/")
            or project.query
            or project.fragment
        ):
            raise ValueError
        ref = project_host.removesuffix(".supabase.co")
        if stage == "prod":
            if value("FURBEBE_PROD_PROJECT_REF") != ref:
                raise ValueError
            if value("SUPABASE_URL_dev") == value("SUPABASE_URL_prod"):
                raise ValueError
        host = url.host or ""
        direct = host == "db." + project_host
        pooled = host.endswith(".pooler.supabase.com") and (url.username or "").endswith("." + ref)
        if (
            not (direct or pooled)
            or url.drivername not in {"postgresql", "postgresql+psycopg"}
            or url.port != 5432
            or url.database != "postgres"
            or not url.username
            or not url.password
            or "YOUR-PASSWORD" in url.password.upper()
            or set(url.query) & CONNECTION_OVERRIDES
            or any(os.environ.get(key) for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"))
        ):
            raise ValueError
        for key, expected in (
            (f"host_{stage}", host),
            (f"port_{stage}", str(url.port)),
            (f"database_{stage}", url.database),
            (f"user_{stage}", url.username),
        ):
            if value(key) and value(key) != expected:
                raise ValueError
        query = dict(url.query)
        query.setdefault("sslmode", "require")
        if query["sslmode"] not in {"require", "verify-ca", "verify-full"}:
            raise ValueError
        return Settings(
            _env_file=None,
            app_env=expected_env,
            frontend_origin=value("FRONTEND_ORIGIN")
            or (
                "https://furbebe.site,https://www.furbebe.site"
                if stage == "prod"
                else "http://localhost:5173"
            ),
            db_pool_size=value("DB_POOL_SIZE") or (1 if stage == "prod" else 5),
            db_max_overflow=value("DB_MAX_OVERFLOW") or (1 if stage == "prod" else 5),
            db_pool_timeout=value("DB_POOL_TIMEOUT") or 5,
            db_pool_recycle=value("DB_POOL_RECYCLE") or 1800,
            db_connect_timeout=value("DB_CONNECT_TIMEOUT") or 5,
            db_statement_timeout_ms=value("DB_STATEMENT_TIMEOUT_MS") or 5000,
            database_url=url.set(query=query).render_as_string(hide_password=False),
        )
    except (ArgumentError, ValueError, TypeError, OSError):
        label = "PROD" if stage == "prod" else "DEV"
        raise ConfigurationError(
            f"Invalid or mismatched Supabase {label} database settings"
        ) from None


def get_dev_database_settings(env_file: Path | None = None) -> Settings:
    return _get_supabase_database_settings("dev", env_file)


def get_prod_database_settings(env_file: Path | None = None) -> Settings:
    return _get_supabase_database_settings("prod", env_file)


def get_operational_settings(target: str | None = None) -> Settings:
    target = target or os.environ.get(TARGET_ENV, "local")
    if target == "supabase-dev":
        return get_dev_database_settings()
    if target == "supabase-prod":
        return get_prod_database_settings()
    if target == "local":
        return get_settings()
    raise ConfigurationError("Unknown operational database target")
