# ==========================================
# AMIS OCR System - Production Dockerfile
# Multi-stage build - Railway Ready
# ==========================================

# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim as builder

WORKDIR /app

# Build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.11-slim

LABEL maintainer="AMIS OCR Team"
LABEL version="1.0.0"
LABEL description="OCR system for AMIS invoices using Claude AI"

WORKDIR /app

# Runtime deps
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy python packages
COPY --from=builder /root/.local /root/.local

# Copy app
COPY backend ./backend
COPY frontend ./frontend

# Runtime dirs
RUN mkdir -p uploads outputs logs

# Env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PORT=8000

# Expose for documentation only
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c "curl -f http://localhost:${PORT:-8000}/health || exit 1"

# START APP
CMD sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
