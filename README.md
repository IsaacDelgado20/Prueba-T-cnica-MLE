# 🏦 BBVA Colombia - Asistente RAG

Sistema de **Retrieval-Augmented Generation (RAG)** que permite consultar información del sitio web institucional de BBVA Colombia mediante un asistente conversacional inteligente.

## 📋 Tabla de Contenidos

- [Arquitectura](#-arquitectura)
- [Stack Tecnológico](#-stack-tecnológico)
- [Patrones de Diseño](#-patrones-de-diseño)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación y Ejecución](#-instalación-y-ejecución)
- [Uso del Sistema](#-uso-del-sistema)
- [Configuración](#-configuración)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Analíticas](#-analíticas)
- [Limitaciones Conocidas](#-limitaciones-conocidas)
- [Futuras Mejoras](#-futuras-mejoras)

---

## 🏗️ Arquitectura

El proyecto implementa **Arquitectura Hexagonal (Ports & Adapters)**, separando claramente las responsabilidades:

```
src/
├── domain/                  # 🔵 CAPA DE DOMINIO (centro)
│   ├── entities.py          #    Entidades: Document, Chunk, Conversation, Message
│   └── ports.py             #    Puertos (interfaces abstractas)
│
├── application/             # 🟢 CAPA DE APLICACIÓN (casos de uso)
│   ├── scraping_service.py  #    Orquesta scraping + indexación
│   ├── rag_service.py       #    Orquesta retrieval + generación
│   └── analytics_service.py #    Métricas del historial
│
├── infrastructure/          # 🟠 CAPA DE INFRAESTRUCTURA (adaptadores)
│   ├── config.py            #    Configuración externalizada
│   ├── container.py         #    Factory + DI Container
│   ├── selenium_scraper.py  #    Adaptador: Selenium WebDriver
│   ├── chroma_store.py      #    Adaptador: ChromaDB vector store
│   ├── embedding_adapter.py #    Adaptador: Sentence Transformers
│   ├── llm_adapter.py       #    Adaptador: Ollama / OpenAI (Strategy)
│   ├── reranker_adapter.py  #    Adaptador: Cross-Encoder reranker
│   ├── conversation_repo.py #    Adaptador: SQLite (Repository)
│   └── document_repo.py     #    Adaptador: File system (Repository)
│
└── interfaces/              # 🔴 ADAPTADORES DE ENTRADA
    ├── api.py               #    REST API (FastAPI)
    └── web_ui.py            #    UI Web (Streamlit)
```

### Flujo del Sistema

```
Usuario → Streamlit UI → FastAPI API → RAG Service
                                           ↓
                                    Embedding (query)
                                           ↓
                                    ChromaDB (búsqueda vectorial)
                                           ↓
                                    Cross-Encoder (reranking)
                                           ↓
                                    Ollama LLM (generación)
                                           ↓
                                    Respuesta + Persistencia
```

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Justificación |
|---|---|---|
| **Lenguaje** | Python 3.11 | Requerimiento del proyecto |
| **Web Scraping** | Selenium + BeautifulSoup | Selenium maneja contenido dinámico (JS); BS4 para parsing HTML |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) | Modelo ligero, gratuito, excelente calidad para español |
| **Vector Store** | ChromaDB | Self-hosted, gratuito, fácil integración, API sencilla |
| **LLM** | Ollama (`llama3.2`) | Self-hosted, gratuito, sin dependencia de APIs externas |
| **Reranker** | Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) | Mejora significativa en relevancia, modelo pequeño |
| **API** | FastAPI | Alta performance, documentación automática, tipado fuerte |
| **UI** | Streamlit | Desarrollo rápido de interfaces funcionales en Python |
| **BD Conversaciones** | SQLite | Ligero, sin servidor, suficiente para el caso de uso |
| **Contenedores** | Docker + Docker Compose | Portabilidad, reproducibilidad, un solo comando |

---

## 🎨 Patrones de Diseño

### 1. Strategy Pattern (Comportamental)

**Dónde:** `src/infrastructure/llm_adapter.py`, `src/domain/ports.py`

**Implementación:** Las clases `OllamaLLMAdapter` y `OpenAILLMAdapter` implementan la interfaz `LLMPort`. El `ServiceContainer` selecciona la estrategia correcta en runtime según la configuración (`LLM_PROVIDER`).

**Por qué:** Permite cambiar de proveedor LLM (Ollama, OpenAI, Groq) sin modificar la lógica de negocio. Solo se cambia una variable de entorno. Mismo principio aplica para `EmbeddingPort` con diferentes proveedores de embeddings.

```python
# La selección se hace en el Factory:
if provider == "ollama":
    self._llm = OllamaLLMAdapter(...)
elif provider in ("openai", "groq"):
    self._llm = OpenAILLMAdapter(...)
```

### 2. Repository Pattern (Estructural)

**Dónde:** `src/infrastructure/conversation_repo.py`, `src/infrastructure/document_repo.py`

**Implementación:** `SQLiteConversationRepository` implementa `ConversationRepository` y `FileDocumentRepository` implementa `DocumentRepository`. Ambas interfaces están definidas en `src/domain/ports.py`.

**Por qué:** Desacopla la lógica de persistencia del dominio. Si se quisiera migrar de SQLite a PostgreSQL, o de archivos a S3, solo se crea un nuevo adaptador sin tocar la capa de aplicación ni el dominio.

### 3. Factory Pattern (Creacional)

**Dónde:** `src/infrastructure/container.py` - clase `ServiceContainer`

**Implementación:** El `ServiceContainer` centraliza la creación de todos los servicios y adaptadores. Métodos como `get_llm()`, `get_embedding()`, `get_rag_service()` actúan como factory methods que crean la implementación correcta basándose en la configuración.

**Por qué:** Centraliza la lógica de creación de objetos complejos y el cableado de dependencias (Dependency Injection). Evita que los componentes tengan que conocer los detalles de construcción de sus dependencias.

### 4. Singleton Pattern (Creacional) - Bonus

**Dónde:** `src/infrastructure/container.py` - método `ServiceContainer.instance()`

**Implementación:** Acceso singleton al contenedor de servicios, garantizando que todos los componentes compartan las mismas instancias de servicios.

**Por qué:** Evita la creación duplicada de componentes costosos (modelos ML, conexiones a BD) y asegura coherencia en toda la aplicación.

---

## 📦 Requisitos Previos

- **Docker** (v20.10+)
- **Docker Compose** (v2.0+)
- **8GB+ RAM** recomendado (Ollama + modelos ML)
- **~10GB disco** (imágenes Docker + modelos)

---

## 🚀 Instalación y Ejecución

### Opción 1: Script automatizado (Linux/Mac)

```bash
# Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd bbva-rag-assistant

# Dar permisos y ejecutar
chmod +x setup.sh
./setup.sh
```

### Opción 2: Paso a paso (Windows/Linux/Mac)

```bash
# 1. Clonar el repositorio
git clone <URL_DEL_REPOSITORIO>
cd bbva-rag-assistant

# 2. Crear archivo de configuración
cp .env.example .env
# Editar .env si es necesario

# 3. Crear directorios de datos
mkdir -p data/raw data/clean

# 4. Levantar servicios base
docker compose up -d chrome chroma ollama

# 5. Esperar ~30 segundos a que Ollama inicie, luego descargar el modelo
docker compose exec ollama ollama pull llama3.2

# 6. Levantar todos los servicios
docker compose up -d --build
```

### Verificar que todo funciona

```bash
# Verificar servicios
docker compose ps

# Verificar health de la API
curl http://localhost:8000/health
# Debería retornar: {"status":"ok"}
```

### URLs de acceso

| Servicio | URL |
|---|---|
| **UI Web (Streamlit)** | http://localhost:8501 |
| **API REST (FastAPI)** | http://localhost:8000 |
| **Swagger Docs** | http://localhost:8000/docs |
| **ChromaDB** | http://localhost:8100 |
| **Ollama** | http://localhost:11434 |
| **Selenium VNC** | http://localhost:7900 (pass: `secret`) |

---

## 💬 Uso del Sistema

### 1. Realizar Web Scraping

1. Abre http://localhost:8501
2. En el sidebar izquierdo, sección **Web Scraping**
3. Configura la URL (por defecto: `https://www.bbva.com.co/`)
4. Ajusta el número máximo de páginas
5. Haz clic en **Iniciar Scraping**
6. Espera a que termine (puede tomar varios minutos)

### 2. Hacer Preguntas

1. En la pestaña **Chat**, escribe tu pregunta
2. Ejemplos de preguntas:
   - "¿Qué tipos de tarjetas de crédito ofrece BBVA?"
   - "¿Cómo abrir una cuenta de ahorros?"
   - "¿Qué seguros tiene disponibles BBVA Colombia?"
   - "¿Cuáles son los beneficios de la banca digital?"

### 3. Gestión de Conversaciones

- Cada conversación tiene un ID único
- Puedes crear nuevas conversaciones con **Nueva Conversación**
- Las conversaciones se persisten automáticamente
- Puedes cargar conversaciones anteriores desde el sidebar

### 4. Ver Analíticas

- Ve a la pestaña **Analíticas**
- Visualiza métricas de uso, keywords frecuentes, tiempos de respuesta

---

## ⚙️ Configuración

Todas las variables son configurables via `.env`:

| Variable | Default | Descripción |
|---|---|---|
| `SCRAPE_MAX_PAGES` | 30 | Máximo de páginas a scrapear |
| `CHUNK_SIZE` | 500 | Tamaño de cada chunk de texto |
| `CHUNK_OVERLAP` | 50 | Solapamiento entre chunks |
| `LLM_PROVIDER` | ollama | Proveedor: `ollama`, `openai`, `groq` |
| `LLM_MODEL` | llama3.2 | Modelo a usar |
| `RERANKER_ENABLED` | true | Habilitar/deshabilitar reranker |
| `HISTORY_MESSAGES` | 10 | N mensajes previos en contexto |
| `RETRIEVE_K` | 10 | Chunks recuperados por búsqueda |
| `RERANK_TOP_K` | 3 | Chunks tras reranking |

### Usar Groq (alternativa gratuita más ligera)

```env
LLM_PROVIDER=groq
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
LLM_API_KEY=gsk_TU_API_KEY
```

Obtén tu API key gratis en: https://console.groq.com/

---

## 📡 Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/scrape` | Iniciar scraping e indexación |
| `POST` | `/chat` | Enviar pregunta al chatbot |
| `GET` | `/conversations` | Listar conversaciones |
| `GET` | `/conversations/{id}` | Obtener conversación por ID |
| `DELETE` | `/conversations/{id}` | Eliminar conversación |
| `GET` | `/analytics` | Métricas generales |
| `GET` | `/analytics/conversations` | Detalle por conversación |
| `GET` | `/index/count` | Cantidad de chunks indexados |

Documentación interactiva completa en: http://localhost:8000/docs

---

## 📊 Analíticas

El módulo de analíticas permite recorrer el histórico de conversaciones para extraer:

- **Total de conversaciones y mensajes**
- **Promedio de mensajes por conversación**
- **Tiempo de respuesta promedio**
- **Top keywords en preguntas de usuarios**
- **Longitud promedio de preguntas y respuestas**
- **Distribución temporal de conversaciones**
- **Detalle individual por conversación**

Accesible desde la UI (pestaña Analíticas) o via API (`/analytics`).

---

## ⚠️ Limitaciones Conocidas

1. **Recursos**: Ollama + modelos ML requieren ~8GB RAM mínimo.
2. **Scraping**: Algunos elementos dinámicos de BBVA.com.co pueden no cargarse completamente con el timeout configurado.
3. **Modelo LLM**: `llama3.2` (3B parámetros) tiene capacidad limitada vs modelos más grandes. Las respuestas pueden no ser perfectas.
4. **Embeddings multilingüe**: `all-MiniLM-L6-v2` fue entrenado principalmente en inglés, aunque funciona razonablemente bien en español.
5. **Concurrencia**: SQLite no soporta escrituras concurrentes masivas.
6. **Primer inicio**: La descarga de modelos ML puede tomar varios minutos la primera vez.

### Decisiones de Diseño

- Se eligió **SQLite** sobre PostgreSQL por simplicidad de deployment (no requiere servidor adicional).
- Se usa un **único Dockerfile** con diferentes `command` en docker-compose para evitar duplicación.
- Los datos crudos y limpios se almacenan en el **filesystem** (no en BD) para facilitar inspección manual.
- El **reranker** es opcional y configurable para equipos con recursos limitados.

---

## 🔮 Futuras Mejoras

1. **Embeddings multilingüe**: Migrar a un modelo como `paraphrase-multilingual-MiniLM-L12-v2` optimizado para español.
2. **Scraping incremental**: Detectar contenido ya scrapeado y solo actualizar cambios.
3. **Streaming**: Implementar respuestas streaming del LLM para mejor UX.
4. **Autenticación**: Agregar autenticación JWT para la API.
5. **Cache**: Implementar caché de respuestas frecuentes.
6. **Tests**: Agregar tests unitarios e integración con pytest.
7. **Monitoring**: Integrar métricas con Prometheus/Grafana.
8. **Multi-tenant**: Soporte para múltiples usuarios con sesiones separadas.
9. **PDF/Docs**: Extender el scraping para incluir documentos PDF del sitio.
10. **Fine-tuning**: Ajustar el modelo con datos específicos del dominio bancario.

---

## 📄 Licencia

Proyecto académico - Prueba técnica BBVA Colombia.
