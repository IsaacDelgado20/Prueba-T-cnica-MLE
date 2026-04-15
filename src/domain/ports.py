"""
Puertos (interfaces) del dominio - Arquitectura Hexagonal.
Define los contratos que deben implementar los adaptadores externos.

Principio de Inversión de Dependencias (DIP): las capas externas
dependen de estas abstracciones, nunca al revés.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.entities import Chunk, Conversation, Document


class ScraperPort(ABC):
    """Puerto de salida para web scraping."""

    @abstractmethod
    def scrape(self, url: str, max_pages: int = 20) -> List[Document]:
        """Scrapea un sitio web y retorna los documentos encontrados."""
        ...


class EmbeddingPort(ABC):
    """Puerto de salida para generación de embeddings (Strategy Pattern)."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings vectoriales para una lista de textos."""
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """Retorna la dimensión de los embeddings generados."""
        ...


class VectorStorePort(ABC):
    """Puerto de salida para almacenamiento y búsqueda vectorial."""

    @abstractmethod
    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Agrega chunks con sus embeddings al store."""
        ...

    @abstractmethod
    def search(self, query_embedding: List[float], k: int = 5) -> List[Chunk]:
        """Busca los k chunks más similares al query embedding."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Retorna el número total de chunks indexados."""
        ...

    @abstractmethod
    def delete_collection(self) -> None:
        """Elimina la colección completa del store."""
        ...


class LLMPort(ABC):
    """Puerto de salida para interacción con LLM (Strategy Pattern)."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Genera una respuesta a partir del prompt dado."""
        ...


class RerankerPort(ABC):
    """Puerto de salida para reranking de resultados."""

    @abstractmethod
    def rerank(self, query: str, chunks: List[Chunk], top_k: int = 3) -> List[Chunk]:
        """Reordena chunks por relevancia respecto al query."""
        ...


class ConversationRepository(ABC):
    """Puerto de repositorio para persistencia de conversaciones (Repository Pattern)."""

    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        """Persiste una conversación (insert o update)."""
        ...

    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Obtiene una conversación por su ID."""
        ...

    @abstractmethod
    def list_all(self) -> List[Conversation]:
        """Lista todas las conversaciones ordenadas por fecha."""
        ...

    @abstractmethod
    def delete(self, conversation_id: str) -> None:
        """Elimina una conversación por su ID."""
        ...


class DocumentRepository(ABC):
    """Puerto de repositorio para persistencia de documentos (Repository Pattern)."""

    @abstractmethod
    def save_raw(self, document: Document) -> None:
        """Guarda el contenido crudo (HTML) del documento."""
        ...

    @abstractmethod
    def save_clean(self, document: Document) -> None:
        """Guarda el contenido limpio (texto) del documento."""
        ...

    @abstractmethod
    def list_documents(self) -> List[Dict]:
        """Lista los metadatos de todos los documentos almacenados."""
        ...
