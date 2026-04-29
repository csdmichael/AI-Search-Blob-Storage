# ── API container image ──────────────────────────────────────────────
# Packages all runtime dependencies inside the image so Azure App Service
# just pulls and runs it — no Oryx, no Kudu, no GLIBC issues.
FROM python:3.12-slim

WORKDIR /app

# Install OS-level deps for cryptography / cffi wheels
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements-api.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py startup.sh ./
COPY api/ api/
COPY config/ config/
COPY scripts/ scripts/
COPY data/ data/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["gunicorn", "app:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "240"]
