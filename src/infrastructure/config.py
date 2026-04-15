"""
Configuración externalizada via variables de entorno / archivo .env.
Usa pydantic-settings para validación y tipado fuerte.
"""

from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración centralizada del sistema con validación."""

    # --- Scraping ---
    SELENIUM_REMOTE_URL: str = Field(
        default="http://chrome:4444/wd/hub",
        description="URL del WebDriver remoto de Selenium",
    )
    SCRAPE_URL: str = Field(
        default="https://www.bbva.com.co/",
        description="URL objetivo para scraping",
    )
    SCRAPE_MAX_PAGES: int = Field(default=30, ge=1, le=200, description="Máximo de páginas a scrapear")

    # --- Chunking ---
    CHUNK_SIZE: int = Field(default=500, ge=100, le=5000, description="Tamaño de chunk en caracteres")
    CHUNK_OVERLAP: int = Field(default=50, ge=0, le=500, description="Solapamiento entre chunks")

    # --- Embedding ---
    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        description="Modelo de sentence-transformers para embeddings",
    )

    # --- Vector Store (ChromaDB) ---
    CHROMA_HOST: str = Field(default="chroma", description="Host de ChromaDB")
    CHROMA_PORT: int = Field(default=8000, ge=1, le=65535, description="Puerto de ChromaDB")
    CHROMA_COLLECTION: str = Field(
        default="bbva_docs", description="Nombre de la colección en ChromaDB"
    )

    # --- LLM ---
    LLM_PROVIDER: str = Field(
        default="ollama",
        description="Proveedor de LLM: ollama, openai, groq",
    )
    LLM_BASE_URL: str = Field(
        default="http://ollama:11434/v1",
        description="URL base de la API del LLM",
    )
    LLM_MODEL: str = Field(
        default="llama3.2",
        description="Nombre del modelo LLM",
    )
    LLM_API_KEY: SecretStr = Field(
        default="ollama",
        description="API key del LLM (usar 'ollama' para Ollama)",
    )
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0, description="Temperatura del LLM")
    LLM_MAX_TOKENS: int = Field(default=1024, ge=64, le=16384, description="Máximo de tokens en respuesta")

    # --- System Prompt ---
    SYSTEM_PROMPT: str = Field(
        default="Eres un asistente virtual de BBVA Colombia. Responde en español.",
        description="Prompt de sistema base para el LLM",
    )

    # --- Reranker ---
    RERANKER_ENABLED: bool = Field(
        default=True, description="Habilitar reranker con cross-encoder"
    )
    RERANKER_MODEL: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Modelo cross-encoder para reranking",
    )

    # --- RAG ---
    RETRIEVE_K: int = Field(default=10, ge=1, le=100, description="Chunks a recuperar en búsqueda")
    RERANK_TOP_K: int = Field(default=3, ge=1, le=50, description="Chunks después de reranking")
    HISTORY_MESSAGES: int = Field(
        default=10, ge=0, le=100, description="N mensajes previos a incluir en el contexto"
    )

    # --- Almacenamiento ---
    DATA_DIR: str = Field(default="./data", description="Directorio de datos")
    DB_PATH: str = Field(
        default="./data/conversations.db",
        description="Ruta de la base de datos SQLite",
    )

    # --- API ---
    API_HOST: str = Field(default="0.0.0.0", description="Host de la API")
    API_PORT: int = Field(default=8000, ge=1, le=65535, description="Puerto de la API")
    LOG_LEVEL: str = Field(default="INFO", description="Nivel de logging (DEBUG, INFO, WARNING, ERROR)")

    # --- UI ---
    API_URL: str = Field(
        default="http://api:8000",
        description="URL de la API para la UI de Streamlit",
    )

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        allowed = {"ollama", "openai", "groq"}
        if v.lower() not in allowed:
            raise ValueError(f"LLM_PROVIDER debe ser uno de {allowed}, recibido: '{v}'")
        return v.lower()

    @field_validator("CHUNK_OVERLAP")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        chunk_size = info.data.get("CHUNK_SIZE", 500)
        if v >= chunk_size:
            raise ValueError(f"CHUNK_OVERLAP ({v}) debe ser menor que CHUNK_SIZE ({chunk_size})")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL debe ser uno de {allowed}")
        return v.upper()

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
