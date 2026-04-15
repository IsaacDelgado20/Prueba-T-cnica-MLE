#!/bin/bash
# =============================================================================
# Script de setup para BBVA RAG Assistant
# Ejecutar: chmod +x setup.sh && ./setup.sh
# =============================================================================

set -e

echo "========================================"
echo "  BBVA RAG Assistant - Setup"
echo "========================================"
echo ""

# 1. Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📄 Creando archivo .env desde .env.example..."
    cp .env.example .env
    echo "   ✅ Archivo .env creado. Edítalo si necesitas cambiar la configuración."
else
    echo "📄 Archivo .env ya existe."
fi

# 2. Crear directorios de datos
echo "📁 Creando directorios de datos..."
mkdir -p data/raw data/clean

# 3. Levantar servicios base
echo ""
echo "🐳 Levantando servicios (Chrome, ChromaDB, Ollama)..."
docker compose up -d chrome chroma ollama
echo "   ✅ Servicios base levantados."

# 4. Esperar a que Ollama esté listo
echo ""
echo "⏳ Esperando a que Ollama esté listo..."
sleep 10

# Verificar que Ollama responde
MAX_RETRIES=30
RETRY_COUNT=0
until docker compose exec -T ollama ollama list > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "   ❌ Ollama no respondió después de ${MAX_RETRIES} intentos."
        echo "   Puedes intentar manualmente: docker compose exec ollama ollama pull llama3.2"
        break
    fi
    echo "   Reintentando ($RETRY_COUNT/$MAX_RETRIES)..."
    sleep 5
done

# 5. Descargar modelo LLM
echo ""
echo "📥 Descargando modelo LLM (llama3.2)... Esto puede tomar varios minutos."
docker compose exec -T ollama ollama pull llama3.2
echo "   ✅ Modelo descargado."

# 6. Levantar todos los servicios
echo ""
echo "🚀 Levantando todos los servicios..."
docker compose up -d --build
echo "   ✅ Todos los servicios levantados."

# 7. Mostrar estado
echo ""
echo "========================================"
echo "  ✅ Setup completado!"
echo "========================================"
echo ""
echo "  🌐 UI Web (Streamlit): http://localhost:8501"
echo "  📡 API (FastAPI):      http://localhost:8000"
echo "  📚 API Docs (Swagger): http://localhost:8000/docs"
echo "  🔍 ChromaDB:           http://localhost:8100"
echo "  🤖 Ollama:             http://localhost:11434"
echo "  🖥️  Selenium VNC:      http://localhost:7900 (pass: secret)"
echo ""
echo "  Próximos pasos:"
echo "  1. Abre http://localhost:8501 en tu navegador"
echo "  2. Haz clic en 'Iniciar Scraping' en el sidebar"
echo "  3. Espera a que termine el scraping"
echo "  4. ¡Haz preguntas sobre BBVA Colombia!"
echo ""
