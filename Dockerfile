# ── Stage 1: dependency install ───────────────────────────────────────────────
# Separate layer so pip doesn't re-run on every code change.
FROM python:3.11-slim AS deps

WORKDIR /app

# psycopg2-binary needs libpq; paramiko needs gcc + libffi
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source (no venv, no .env, no uploads — handled by .dockerignore)
COPY api/ ./api/

# Create runtime directories the app expects
RUN mkdir -p uploads data_sources

# Run as non-root for security
RUN useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

# Railway injects $PORT; fall back to 8000 for local docker-compose runs.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
