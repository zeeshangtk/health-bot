# Multi-stage Dockerfile for Telegram Bot
# Supports build-time secrets and multi-arch builds (linux/amd64, linux/arm64)

# Stage 1: Builder - Install dependencies
FROM python:3.13-slim as builder

# Set build arguments (can be used for build-time secrets)
ARG BUILDKIT_INLINE_CACHE=1
ARG PIP_EXTRA_INDEX_URL
ARG PIP_TRUSTED_HOST

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create and use a non-root user for building
RUN useradd -m -u 1000 builder && \
    mkdir -p /app && \
    chown -R builder:builder /app

USER builder
WORKDIR /app

# Copy requirements first for better layer caching
COPY --chown=builder:builder requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --user --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.13-slim as runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

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

# Ensure local bin directory is in PATH
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check (basic process check)
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python.*bot.py" > /dev/null || exit 1

# Default command
CMD ["python", "bot.py"]



