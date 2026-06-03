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

# Runtime system libs (add postgresql-client for psql command)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source (no venv, no .env, no uploads — handled by .dockerignore)
COPY api/ ./api/
COPY migrations/ ./migrations/
COPY start.sh ./start.sh

# Make startup script executable
RUN chmod +x start.sh

# Create the uploads directory the app writes to
RUN mkdir -p uploads

# Run as non-root for security
RUN useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

# Railway injects $PORT; fall back to 8000 for local docker-compose runs.
EXPOSE 8000
CMD ["./start.sh"]
