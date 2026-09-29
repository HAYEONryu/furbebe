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


def get_dev_database_settings(env_file: Path | None = None) -> Settings:
    """Match the PostgreSQL target to the user's explicitly named DEV project."""
    try:
        values = dotenv_values(env_file or ROOT / ".env", interpolate=False, encoding="utf-8-sig")

        def value(key):
            return os.environ.get(key, values.get(key))

        if value("APP_ENV") not in (None, "", "development"):
            raise ValueError
        url = make_url(value("DATABASE_URL_dev") or "")
        project = urlsplit(value("SUPABASE_URL_dev") or "")
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
            ("host_dev", host),
            ("port_dev", str(url.port)),
            ("database_dev", url.database),
            ("user_dev", url.username),
        ):
            if value(key) and value(key) != expected:
                raise ValueError
        query = dict(url.query)
        query.setdefault("sslmode", "require")
        if query["sslmode"] not in {"require", "verify-ca", "verify-full"}:
            raise ValueError
        return Settings(
            # Keep the same dotenv/environment precedence as the regular app.
            # The explicitly validated DEV URL still overrides DATABASE_URL.
            _env_file=env_file or ROOT / ".env",
            app_env="development",
            database_url=url.set(query=query).render_as_string(hide_password=False),
        )
    except (ArgumentError, ValueError, TypeError, OSError):
        raise ConfigurationError("Invalid or mismatched Supabase DEV database settings") from None


def get_operational_settings(target: str | None = None) -> Settings:
    target = target or os.environ.get(TARGET_ENV, "local")
    if target == "supabase-dev":
        return get_dev_database_settings()
    if target == "local":
        return get_settings()
    raise ConfigurationError("Unknown operational database target")
