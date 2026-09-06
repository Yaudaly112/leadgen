# ── Build stage ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies (gcc for compiling asyncpg)
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime deps for asyncpg
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/ ./

# Create non-root user
RUN groupadd -r leadgen && useradd -r -g leadgen leadgen
RUN mkdir -p /app/generated_sites && chown -R leadgen:leadgen /app
USER leadgen

# Expose port
EXPOSE 8000

# Run with production settings
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
