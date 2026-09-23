# ════════════════════════════════════════════════════════════════════
# Memories API — imagen multi-etapa
#   development: recarga en caliente, monta el codigo por volumen
#   production : sin recarga, varios workers
# ════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─── Dependencias (capa cacheable) ──────────────────────────────────
FROM base AS dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# ─── Desarrollo ─────────────────────────────────────────────────────
FROM dependencies AS development
RUN pip install -r requirements-dev.txt
COPY . .
RUN chmod +x scripts/entrypoint.sh \
    && mkdir -p /app/storage
EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── Produccion ─────────────────────────────────────────────────────
FROM dependencies AS production
COPY . .
RUN chmod +x scripts/entrypoint.sh \
    && mkdir -p /app/storage \
    && addgroup --system memories \
    && adduser --system --ingroup memories memories \
    && chown -R memories:memories /app
USER memories
EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
