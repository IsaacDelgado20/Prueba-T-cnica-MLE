# 🏦 BBVA RAG Assistant — Guía Completa de Instalación y Ejecución

## Tabla de Contenidos

1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Prerrequisitos de Software](#3-prerrequisitos-de-software)
4. [Instalación Paso a Paso](#4-instalación-paso-a-paso)
5. [Configuración](#5-configuración)
6. [Ejecución con Docker Compose](#6-ejecución-con-docker-compose)
7. [Ejecución Local (sin Docker)](#7-ejecución-local-sin-docker)
8. [Uso del Sistema](#8-uso-del-sistema)
9. [API REST — Endpoints](#9-api-rest--endpoints)
10. [Estructura del Proyecto](#10-estructura-del-proyecto)
11. [Buenas Prácticas Aplicadas](#11-buenas-prácticas-aplicadas)
12. [Solución de Problemas](#12-solución-de-problemas)

---

## 1. Descripción del Proyecto

Sistema conversacional RAG (Retrieval-Augmented Generation) para BBVA Colombia que:

- **Scraping**: Recorre el sitio web de BBVA Colombia usando Selenium para extraer contenido.
- **Indexación**: Divide el contenido en chunks, genera embeddings con sentence-transformers y los almacena en ChromaDB.
- **Consulta RAG**: Ante una pregunta del usuario, recupera chunks relevantes, los reordena con un Cross-Encoder y genera una respuesta con el LLM.
- **Analíticas**: Dashboard con métricas de uso, keywords frecuentes y tiempos de respuesta.

---

## 2. Arquitectura del Sistema

El proyecto sigue una **Arquitectura Hexagonal (Ports & Adapters)**:

```
┌──────────────────────────────────────────────────────────────┐
│                    INTERFACES (Inbound)                       │
│   ┌──────────────┐      ┌──────────────┐                     │
│   │  FastAPI REST │      │  Streamlit   │                     │
│   │   (api.py)   │      │  (web_ui.py) │                     │
│   └──────┬───────┘      └──────┬───────┘                     │
├──────────┼─────────────────────┼─────────────────────────────┤
│          │   APPLICATION SERVICES                             │
│   ┌──────┴──────────────────────┴──────┐                     │
│   │  ScrapingService │ RAGService │ AnalyticsService         │
│   └──────┬──────────────────────┬──────┘                     │
├──────────┼──────────────────────┼────────────────────────────┤
│          │     DOMAIN (Entities + Ports)                      │
│   ┌──────┴──────────────────────┴──────┐                     │
│   │  Entities (Chunk, Conversation...) │                     │
│   │  Ports (Interfaces abstractas)     │                     │
│   └──────┬──────────────────────┬──────┘                     │
├──────────┼──────────────────────┼────────────────────────────┤
│          │   INFRASTRUCTURE (Outbound Adapters)               │
│   ┌──────┴──────────────────────┴──────────────────────┐     │
│   │  SeleniumScraper │ ChromaVectorStore │ LLMAdapter  │     │
│   │  EmbeddingAdapter│ RerankerAdapter   │ ConvRepo    │     │
│   └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

**Servicios Docker**:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `api` | 8000 | Backend FastAPI |
| `ui` | 8501 | Frontend Streamlit |
| `chrome` | 4444 / 7900 | Selenium WebDriver |
| `chroma` | 8100 | Vector Store ChromaDB |
| `ollama` | 11434 | Servidor LLM Ollama |

---

## 3. Prerrequisitos de Software

### Obligatorios

| Software | Versión mínima | Para qué se usa | Descarga |
|----------|---------------|------------------|----------|
| **Docker Desktop** | 4.20+ | Contenedorización de todos los servicios | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Docker Compose** | 2.20+ | Orquestación multi-contenedor (incluido en Docker Desktop) | Incluido en Docker Desktop |
| **Git** | 2.30+ | Clonar el repositorio | [git-scm.com](https://git-scm.com/) |

### Opcionales (solo para ejecución local sin Docker)

| Software | Versión | Para qué se usa |
|----------|---------|------------------|
| **Python** | 3.11+ | Runtime del código |
| **pip** | 23.0+ | Gestor de paquetes Python |
| **Google Chrome** | Última | Necesario para Selenium (modo local) |
| **ChromeDriver** | Misma versión que Chrome | Driver de Selenium |

### Requisitos de Hardware

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| **RAM** | 8 GB | 16 GB |
| **Disco** | 10 GB libres | 20 GB libres |
| **CPU** | 4 cores | 8 cores |
| **GPU** | No requerida | NVIDIA GPU (acelera Ollama) |

> **Nota**: La primera ejecución descargará modelos de ~2-4 GB (LLM + embeddings + reranker).

---

## 4. Instalación Paso a Paso

### Paso 1: Instalar Docker Desktop

#### Windows
1. Descargar Docker Desktop desde [docker.com](https://www.docker.com/products/docker-desktop/)
2. Ejecutar el instalador `.exe`
3. Reiniciar el equipo si lo solicita
4. Abrir Docker Desktop y verificar que esté corriendo (icono en la barra de tareas)
5. Abrir una terminal y verificar:
   ```powershell
   docker --version
   docker compose version
   ```

#### macOS
```bash
brew install --cask docker
# O descargar desde docker.com
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable docker
sudo usermod -aG docker $USER
# Cerrar sesión y volver a iniciar
```

### Paso 2: Instalar Git

#### Windows
Descargar desde [git-scm.com](https://git-scm.com/) e instalar con opciones por defecto.

#### macOS / Linux
```bash
# macOS
brew install git

# Linux
sudo apt-get install -y git
```

### Paso 3: Clonar / Descargar el Proyecto

```bash
# Opción 1: Si tienes el repositorio en Git
git clone <URL_DEL_REPOSITORIO>
cd bbva-rag-assistant

# Opción 2: Si tienes el ZIP
# Descomprimir y navegar a la carpeta del proyecto
cd "Proyecto Prueba tecnica"
```

### Paso 4: Configurar Variables de Entorno

```bash
# Copiar el archivo de configuración de ejemplo
cp .env.example .env
```

Editar `.env` según tus necesidades (ver [sección 5](#5-configuración)).

---

## 5. Configuración

El archivo `.env` controla toda la configuración del sistema.

### Configuración por Defecto (Ollama — 100% local, gratis)

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=ollama
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048
```

> No requiere API key ni internet después de descargar los modelos.

### Configuración con Groq (Gratis, más rápido, requiere internet)

```env
LLM_PROVIDER=groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
LLM_API_KEY=gsk_TU_API_KEY_AQUI
```

Para obtener tu API key gratis:
1. Ir a [console.groq.com](https://console.groq.com/)
2. Crear una cuenta
3. Generar una API key en "API Keys"

### Configuración con OpenAI (De pago)

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
LLM_API_KEY=sk-TU_API_KEY_AQUI
```

### Variables Importantes

| Variable | Default | Descripción |
|----------|---------|-------------|
| `CHUNK_SIZE` | 500 | Tamaño de cada fragmento de texto |
| `CHUNK_OVERLAP` | 50 | Solapamiento entre chunks |
| `RETRIEVE_K` | 10 | Chunks a recuperar en búsqueda |
| `RERANK_TOP_K` | 3 | Chunks finales después del reranking |
| `HISTORY_MESSAGES` | 10 | Mensajes de historial en el prompt |
| `LOG_LEVEL` | INFO | Nivel de logging (DEBUG, INFO, WARNING, ERROR) |
| `RERANKER_ENABLED` | true | Activar/desactivar el reranker |
| `SCRAPE_MAX_PAGES` | 30 | Máximo de páginas a scrapear |

---

## 6. Ejecución con Docker Compose

### Iniciar Todos los Servicios

```bash
# Construir imágenes y levantar todos los contenedores
docker compose up --build -d
```

Este comando:
1. Construye la imagen Docker del proyecto
2. Descarga las imágenes de Selenium, ChromaDB y Ollama
3. Inicia los 5 contenedores en segundo plano

### Descargar el Modelo LLM (solo primera vez, si usas Ollama)

```bash
# Descargar el modelo llama3.2 dentro del contenedor de Ollama
docker exec bbva-rag-ollama ollama pull llama3.2
```

> Esto descarga ~2 GB. Solo se hace una vez; el modelo persiste en un volumen Docker.

### Verificar que Todo Esté Corriendo

```bash
# Ver estado de los contenedores
docker compose ps

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f api
```

**Resultado esperado de `docker compose ps`**:

```
NAME              STATUS        PORTS
bbva-rag-api      Up (healthy)  0.0.0.0:8000->8000/tcp
bbva-rag-ui       Up (healthy)  0.0.0.0:8501->8501/tcp
bbva-rag-chrome   Up            0.0.0.0:4444->4444/tcp, 0.0.0.0:7900->7900/tcp
bbva-rag-chroma   Up (healthy)  0.0.0.0:8100->8000/tcp
bbva-rag-ollama   Up            0.0.0.0:11434->11434/tcp
```

### Verificar Health Check de la API

```bash
curl http://localhost:8000/health
# Respuesta esperada: {"status":"ok","version":"1.1.0"}
```

### Detener los Servicios

```bash
# Detener sin eliminar datos
docker compose down

# Detener y eliminar todos los volúmenes (BORRA DATOS)
docker compose down -v
```

---

## 7. Ejecución Local (sin Docker)

### Paso 1: Crear Entorno Virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Paso 2: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 3: Instalar y Configurar Servicios Externos

#### ChromaDB (Vector Store)
```bash
# Opción A: Ejecutar ChromaDB con Docker
docker run -d -p 8100:8000 --name chroma chromadb/chroma:latest

# Opción B: Instalar como paquete Python (ya incluido en requirements.txt)
# ChromaDB se ejecuta embebido si no especificas host
```

#### Ollama (LLM Local)
```bash
# Instalar Ollama (Windows/macOS: descargar desde ollama.ai)
# Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar el servidor
ollama serve

# Descargar el modelo (en otra terminal)
ollama pull llama3.2
```

#### Selenium (Scraping)
```bash
# Opción A: Selenium remoto con Docker
docker run -d -p 4444:4444 -p 7900:7900 --shm-size=2g selenium/standalone-chrome:latest

# Opción B: ChromeDriver local
# Descargar ChromeDriver de la misma versión que tu Chrome
# https://googlechromelabs.github.io/chrome-for-testing/
```

### Paso 4: Configurar .env para Ejecución Local

```env
# Cambiar hosts de Docker a localhost
SELENIUM_REMOTE_URL=http://localhost:4444/wd/hub
CHROMA_HOST=localhost
CHROMA_PORT=8100
LLM_BASE_URL=http://localhost:11434/v1
API_URL=http://localhost:8000
```

### Paso 5: Ejecutar la API

```bash
uvicorn src.interfaces.api:app --host 0.0.0.0 --port 8000 --reload
```

### Paso 6: Ejecutar la UI (en otra terminal)

```bash
export API_URL=http://localhost:8000  # Linux/macOS
set API_URL=http://localhost:8000     # Windows CMD
$env:API_URL="http://localhost:8000"  # Windows PowerShell

streamlit run src/interfaces/web_ui.py --server.port 8501
```

---

## 8. Uso del Sistema

### Acceso

| Interfaz | URL |
|----------|-----|
| **UI Web (Streamlit)** | [http://localhost:8501](http://localhost:8501) |
| **API REST (FastAPI)** | [http://localhost:8000](http://localhost:8000) |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Selenium VNC** | [http://localhost:7900](http://localhost:7900) (password: `secret`) |

### Flujo de Uso

1. **Abrir la UI** en `http://localhost:8501`
2. **Hacer Scraping**: En el sidebar, clic en "🚀 Iniciar Scraping" (puede tomar 5-15 minutos)
3. **Verificar indexación**: El contador de "Chunks indexados" debe ser > 0
4. **Hacer preguntas**: Usar el chat para consultar sobre productos BBVA
5. **Ver analíticas**: Pestaña "📊 Analíticas" para ver métricas y keywords

### Ejemplos de Preguntas

- "¿Qué tipos de tarjetas de crédito ofrece BBVA Colombia?"
- "¿Cuáles son los requisitos para abrir una cuenta de ahorros?"
- "¿Cómo puedo solicitar un crédito hipotecario?"
- "¿Qué beneficios tiene la banca digital de BBVA?"

---

## 9. API REST — Endpoints

### Health Check
```
GET /health
```
Respuesta: `{"status": "ok", "version": "1.1.0"}`

### Scraping
```
POST /scrape
Body: {"url": "https://www.bbva.com.co/", "max_pages": 30}
```
Respuesta: `{"status": "success", "documents": 25, "chunks_indexed": 150, ...}`

### Chat
```
POST /chat
Body: {"question": "¿Qué tarjetas ofrece BBVA?", "conversation_id": null}
```
Respuesta: `{"answer": "...", "conversation_id": "uuid", "sources": [...], "response_time_s": 2.5}`

### Conversaciones
```
GET  /conversations                        — Listar todas
GET  /conversations/{id}                   — Obtener una
DELETE /conversations/{id}                 — Eliminar una
```

### Analíticas
```
GET /analytics                             — Métricas generales
GET /analytics/conversations               — Detalle por conversación
```

### Índice
```
GET /index/count                           — Cantidad de chunks indexados
```

---

## 10. Estructura del Proyecto

```
Proyecto Prueba tecnica/
├── src/
│   ├── domain/                     # Capa de Dominio
│   │   ├── entities.py             # Entidades (Chunk, Conversation, Message)
│   │   └── ports.py                # Puertos (interfaces abstractas)
│   │
│   ├── application/                # Capa de Aplicación
│   │   ├── scraping_service.py     # Orquesta scraping + indexación
│   │   ├── rag_service.py          # Orquesta RAG (retrieve + generate)
│   │   └── analytics_service.py    # Métricas y analíticas
│   │
│   ├── infrastructure/             # Capa de Infraestructura (Adapters)
│   │   ├── config.py               # Settings (Pydantic) + validación
│   │   ├── container.py            # IoC Container (Factory + Singleton)
│   │   ├── selenium_scraper.py     # Adapter: Selenium WebDriver
│   │   ├── chroma_store.py         # Adapter: ChromaDB vector store
│   │   ├── embedding_adapter.py    # Adapter: sentence-transformers
│   │   ├── llm_adapter.py          # Adapter: Ollama/OpenAI/Groq
│   │   ├── reranker_adapter.py     # Adapter: Cross-Encoder reranker
│   │   ├── conversation_repo.py    # Adapter: SQLite repository
│   │   └── document_repo.py        # Adapter: filesystem repository
│   │
│   └── interfaces/                 # Capa de Interfaces (Inbound)
│       ├── api.py                  # FastAPI REST API
│       └── web_ui.py               # Streamlit Web UI
│
├── data/                           # Datos (raw, clean, SQLite DB)
├── diagrams/                       # Diagramas draw.io
├── Dockerfile                      # Multi-stage build
├── docker-compose.yml              # Orquestación de servicios
├── requirements.txt                # Dependencias Python
├── .env                            # Configuración (NO commitear)
├── .env.example                    # Template de configuración
├── .gitignore                      # Archivos ignorados por Git
├── setup.sh                        # Script de setup automatizado
└── README.md                       # Documentación general
```

---

## 11. Buenas Prácticas Aplicadas

### Arquitectura
- **Hexagonal (Ports & Adapters)**: Desacopla dominio de infraestructura
- **Inyección de Dependencias**: Via `ServiceContainer` (IoC)
- **Principio de Inversión de Dependencias (DIP)**: Los servicios dependen de interfaces, no implementaciones

### Python
- **Dataclasses inmutables**: `frozen=True` en value objects (Chunk, Message)
- **Enums para constantes**: `Role` enum en lugar de strings libres
- **Validación con Pydantic**: `field_validator`, `SecretStr`, bounds (`ge`, `le`)
- **Datetime timezone-aware**: `datetime.now(timezone.utc)` en vez del deprecado `utcnow()`
- **Tipado fuerte**: Type hints en todas las funciones
- **Lazy logging**: `logger.info("msg %s", var)` en vez de f-strings

### Patrones de Diseño
- **Singleton thread-safe**: Double-checked locking con `threading.Lock`
- **Template Method**: Base class `_BaseLLMAdapter` para evitar duplicación
- **Strategy Pattern**: Intercambio de proveedores LLM sin cambiar código
- **Context Manager**: Gestión de recursos (Selenium driver, SQLite connections)
- **Retry con backoff**: Reintentos exponenciales en scraping y conexiones

### Infraestructura
- **Multi-stage Docker build**: Imagen final más ligera sin build tools
- **Non-root user**: Seguridad en el contenedor
- **Health checks**: En Docker Compose para dependency ordering
- **WAL mode en SQLite**: Mejor concurrencia en lecturas/escrituras
- **Volúmenes Docker**: Persistencia de datos (ChromaDB, Ollama, modelos)

### Seguridad
- **SecretStr**: API keys nunca en logs
- **CORS configurado**: Control de orígenes
- **Validación de entrada**: Pydantic models en todos los endpoints
- **Error handling**: Excepciones capturadas, sin stack traces al usuario

---

## 12. Solución de Problemas

### Error: "Cannot connect to Docker daemon"
```bash
# Verificar que Docker Desktop esté corriendo
docker info
# Si no está corriendo, abrir Docker Desktop
```

### Error: "Port already in use"
```bash
# Ver qué proceso usa el puerto
# Windows
netstat -ano | findstr :8000
# Linux/macOS
lsof -i :8000

# Cambiar el puerto en docker-compose.yml
```

### Error: "Model not found" (Ollama)
```bash
# Verificar modelos descargados
docker exec bbva-rag-ollama ollama list

# Descargar el modelo
docker exec bbva-rag-ollama ollama pull llama3.2
```

### Error: "Connection refused" a ChromaDB
```bash
# Verificar que el contenedor esté healthy
docker compose ps chroma

# Ver logs
docker compose logs chroma
```

### Scraping lento o sin resultados
- Verificar que el contenedor `chrome` esté corriendo
- Ver el navegador en acción: `http://localhost:7900` (password: `secret`)
- Aumentar `SCRAPE_MAX_PAGES` si necesitas más contenido
- Verificar conectividad a internet desde el contenedor

### Error de memoria / OOM
- Aumentar la memoria asignada a Docker Desktop (Settings > Resources > Memory)
- Mínimo recomendado: 8 GB para Docker

### Los modelos tardan en descargar
Primera ejecución descarga:
- **Ollama llama3.2**: ~2 GB
- **Embedding model** (all-MiniLM-L6-v2): ~90 MB
- **Reranker model** (ms-marco-MiniLM-L-6-v2): ~90 MB

Estos se cachean en volúmenes Docker y no se vuelven a descargar.

### Resetear todos los datos
```bash
# Detener y eliminar volúmenes
docker compose down -v

# Volver a iniciar
docker compose up --build -d

# Re-descargar modelo Ollama
docker exec bbva-rag-ollama ollama pull llama3.2
```

---

## Contacto

Proyecto desarrollado como prueba técnica para BBVA Colombia.
