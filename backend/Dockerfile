FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/

# Verify critical imports are present
RUN python -c "from fastapi import Depends; print('OK: Depends imported')"
RUN grep -n 'Depends' /app/app/main.py || (echo 'ERROR: Depends not found in main.py' && exit 1)

# Create non-root user
RUN groupadd -r leadgen && useradd -r -g leadgen leadgen
RUN mkdir -p /app/generated_sites && chown -R leadgen:leadgen /app
USER leadgen

EXPOSE 8000

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
