"""
Contenedor de Servicios / Factory - Patrón Factory + Singleton.
Centraliza la creación de objetos y el cableado de dependencias
según la configuración de runtime. Thread-safe.
"""

import logging
import threading

from src.application.analytics_service import AnalyticsService
from src.application.rag_service import RAGService
from src.application.scraping_service import ScrapingService
from src.domain.ports import LLMPort, RerankerPort
from src.infrastructure.chroma_store import ChromaVectorStore
from src.infrastructure.config import Settings
from src.infrastructure.conversation_repo import SQLiteConversationRepository
from src.infrastructure.document_repo import FileDocumentRepository
from src.infrastructure.embedding_adapter import SentenceTransformerEmbedding
from src.infrastructure.llm_adapter import OllamaLLMAdapter, OpenAILLMAdapter
from src.infrastructure.reranker_adapter import CrossEncoderReranker
from src.infrastructure.selenium_scraper import SeleniumScraper

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Contenedor de Inyección de Dependencias (Factory + Singleton Pattern).
    Thread-safe: usa locks para garantizar inicialización única.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, settings: Settings = None):
        self._settings = settings or Settings()
        self._init_lock = threading.Lock()
        self._embedding = None
        self._vector_store = None
        self._llm = None
        self._reranker = None
        self._conversation_repo = None
        self._document_repo = None
        self._scraper = None
        self._scraping_service = None
        self._rag_service = None
        self._analytics_service = None

    @classmethod
    def instance(cls, settings: Settings = None) -> "ServiceContainer":
        """Acceso Singleton thread-safe: retorna siempre la misma instancia."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Resetea la instancia singleton (útil para testing)."""
        with cls._lock:
            cls._instance = None

    @property
    def settings(self) -> Settings:
        return self._settings

    def get_embedding(self) -> SentenceTransformerEmbedding:
        if self._embedding is None:
            with self._init_lock:
                if self._embedding is None:
                    self._embedding = SentenceTransformerEmbedding(
                        model_name=self._settings.EMBEDDING_MODEL
                    )
        return self._embedding

    def get_vector_store(self) -> ChromaVectorStore:
        if self._vector_store is None:
            with self._init_lock:
                if self._vector_store is None:
                    self._vector_store = ChromaVectorStore(
                        host=self._settings.CHROMA_HOST,
                        port=self._settings.CHROMA_PORT,
                        collection_name=self._settings.CHROMA_COLLECTION,
                    )
        return self._vector_store

    def get_llm(self) -> LLMPort:
        """Factory Method: crea el adaptador LLM apropiado (Strategy Pattern)."""
        if self._llm is None:
            with self._init_lock:
                if self._llm is None:
                    provider = self._settings.LLM_PROVIDER
                    api_key = self._settings.LLM_API_KEY.get_secret_value()

                    common_kwargs = dict(
                        base_url=self._settings.LLM_BASE_URL,
                        model=self._settings.LLM_MODEL,
                        api_key=api_key,
                        temperature=self._settings.LLM_TEMPERATURE,
                        max_tokens=self._settings.LLM_MAX_TOKENS,
                        system_prompt=self._settings.SYSTEM_PROMPT,
                    )

                    if provider == "ollama":
                        self._llm = OllamaLLMAdapter(**common_kwargs)
                    elif provider in ("openai", "groq"):
                        self._llm = OpenAILLMAdapter(**common_kwargs)
                    else:
                        raise ValueError(f"Proveedor LLM desconocido: {provider}")

                    logger.info(
                        "LLM configurado: provider=%s, model=%s", provider, self._settings.LLM_MODEL
                    )

        return self._llm

    def get_reranker(self) -> RerankerPort:
        if self._reranker is None and self._settings.RERANKER_ENABLED:
            with self._init_lock:
                if self._reranker is None:
                    self._reranker = CrossEncoderReranker(
                        model_name=self._settings.RERANKER_MODEL
                    )
        return self._reranker

    def get_conversation_repo(self) -> SQLiteConversationRepository:
        if self._conversation_repo is None:
            with self._init_lock:
                if self._conversation_repo is None:
                    self._conversation_repo = SQLiteConversationRepository(
                        db_path=self._settings.DB_PATH
                    )
        return self._conversation_repo

    def get_document_repo(self) -> FileDocumentRepository:
        if self._document_repo is None:
            self._document_repo = FileDocumentRepository(
                data_dir=self._settings.DATA_DIR
            )
        return self._document_repo

    def get_scraper(self) -> SeleniumScraper:
        if self._scraper is None:
            self._scraper = SeleniumScraper(
                remote_url=self._settings.SELENIUM_REMOTE_URL
            )
        return self._scraper

    def get_scraping_service(self) -> ScrapingService:
        if self._scraping_service is None:
            self._scraping_service = ScrapingService(
                scraper=self.get_scraper(),
                embedding=self.get_embedding(),
                vector_store=self.get_vector_store(),
                document_repo=self.get_document_repo(),
                chunk_size=self._settings.CHUNK_SIZE,
                chunk_overlap=self._settings.CHUNK_OVERLAP,
            )
        return self._scraping_service

    def get_rag_service(self) -> RAGService:
        if self._rag_service is None:
            self._rag_service = RAGService(
                embedding=self.get_embedding(),
                vector_store=self.get_vector_store(),
                llm=self.get_llm(),
                reranker=self.get_reranker(),
                conversation_repo=self.get_conversation_repo(),
                history_messages=self._settings.HISTORY_MESSAGES,
                retrieve_k=self._settings.RETRIEVE_K,
                rerank_top_k=self._settings.RERANK_TOP_K,
            )
        return self._rag_service

    def get_analytics_service(self) -> AnalyticsService:
        if self._analytics_service is None:
            self._analytics_service = AnalyticsService(
                conversation_repo=self.get_conversation_repo()
            )
        return self._analytics_service
