# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Instrumented sample app image. Multi-stage, non-root, slim base.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first to maximise layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application source.
COPY main.py .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Single worker is plenty for the demo and keeps metrics in one process.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
