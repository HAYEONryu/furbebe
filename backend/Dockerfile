FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY backend/requirements.txt backend/requirements-runtime-lock.txt /app/backend/
RUN python -m pip install -r backend/requirements.txt -c backend/requirements-runtime-lock.txt \
    && useradd --system --uid 10001 --create-home furbebe

# API-only image: no jobs, captures, migrations, tests, virtualenvs or dotenv files.
COPY backend/__init__.py /app/backend/__init__.py
COPY backend/app /app/backend/app
USER 10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=8s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=6)"

# Cloud Run is explicitly configured for container port 8080 and one process.
# Raw Uvicorn access URLs may contain query secrets; safe middleware logs instead.
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log"]
