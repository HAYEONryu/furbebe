FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY backend/requirements.txt backend/requirements-runtime-lock.txt /app/backend/
RUN python -m pip install -r backend/requirements.txt -c backend/requirements-runtime-lock.txt \
    && useradd --system --uid 10001 --create-home furbebe

COPY backend /app/backend
USER 10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=8s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=6)"

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
