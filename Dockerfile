# ============================================================
# Multi-stage build: BBVA RAG Assistant
# ============================================================

# ---------- Stage 1: dependencias ----------
FROM python:3.11-slim AS deps

WORKDIR /app

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python (capa cache independiente)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copiar paquetes instalados desde stage anterior
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Crear usuario no-root por seguridad
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copiar código fuente
COPY . .

# Crear directorios de datos y cache con permisos
RUN mkdir -p data/raw data/clean /home/appuser/.cache && chown -R appuser:appuser data /home/appuser/.cache

# Cambiar a usuario no-root
USER appuser

# Exponer puertos
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5).raise_for_status()" || exit 1

# Comando por defecto: API FastAPI
CMD ["uvicorn", "src.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]
