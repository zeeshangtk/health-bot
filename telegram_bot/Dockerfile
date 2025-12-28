# Multi-stage Dockerfile for Telegram Bot
# Optimized for Raspberry Pi 5 (ARM64) with minimal resource footprint
# Supports multi-arch builds (linux/amd64, linux/arm64)

# Stage 1: Builder - Install dependencies
FROM python:3.13-slim-bookworm AS builder

# Set build arguments (can be used for build-time secrets)
ARG BUILDKIT_INLINE_CACHE=1
ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST

# Install system dependencies for building Python packages
# gcc/g++ needed for compiling native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create and use a non-root user for building
RUN useradd -m -u 1000 builder && \
    mkdir -p /app && \
    chown -R builder:builder /app

USER builder
WORKDIR /app

# Copy requirements first for better layer caching
COPY --chown=builder:builder requirements.txt .

# Install Python dependencies with optimizations
# --no-compile: Skip .pyc generation during install (reduces disk I/O)
# --no-cache-dir: Don't cache pip downloads (smaller image)
RUN pip install --user --no-cache-dir --no-compile --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir --no-compile -r requirements.txt && \
    # Remove unnecessary pip cache and metadata
    find /home/builder/.local -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find /home/builder/.local -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true && \
    find /home/builder/.local -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true

# Stage 2: Runtime - Minimal production image
FROM python:3.13-slim-bookworm AS runtime

# Set labels for image metadata
LABEL org.opencontainers.image.title="Health Bot Telegram"
LABEL org.opencontainers.image.description="Telegram bot for health record management"
LABEL org.opencontainers.image.vendor="health-bot"

# Create non-root user for running the application
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

USER appuser
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=appuser:appuser /home/builder/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Environment configuration optimized for containers
ENV PATH=/home/appuser/.local/bin:$PATH \
    # Don't buffer stdout/stderr - get logs immediately
    PYTHONUNBUFFERED=1 \
    # Don't write .pyc files - saves disk space in container
    PYTHONDONTWRITEBYTECODE=1 \
    # Malloc tuning for lower memory footprint
    MALLOC_ARENA_MAX=2

# Health check (basic process check)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python.*bot.py" > /dev/null || exit 1

# Default command
CMD ["python", "bot.py"]
