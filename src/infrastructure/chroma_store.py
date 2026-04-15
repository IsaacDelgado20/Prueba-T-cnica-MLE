"""
Adaptador ChromaDB - Implementa VectorStorePort.
Almacenamiento y búsqueda vectorial usando ChromaDB con retry de conexión.
"""

import logging
import time
from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.domain.entities import Chunk
from src.domain.ports import VectorStorePort

logger = logging.getLogger(__name__)

_MAX_CONNECT_RETRIES = 5
_RETRY_DELAY_BASE = 2


class ChromaVectorStore(VectorStorePort):
    """Adaptador de ChromaDB para almacenamiento vectorial con retry de conexión."""

    def __init__(self, host: str, port: int, collection_name: str):
        self._host = host
        self._port = port
        self._collection_name = collection_name
        self._client = self._connect_with_retry()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB conectado a %s:%d, colección: %s", host, port, collection_name
        )

    def _connect_with_retry(self) -> chromadb.HttpClient:
        """Conecta a ChromaDB con reintentos."""
        for attempt in range(1, _MAX_CONNECT_RETRIES + 1):
            try:
                client = chromadb.HttpClient(
                    host=self._host,
                    port=self._port,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                client.heartbeat()
                return client
            except Exception as e:
                if attempt < _MAX_CONNECT_RETRIES:
                    wait = _RETRY_DELAY_BASE ** attempt
                    logger.warning(
                        "ChromaDB conexión fallida (intento %d/%d): %s. Reintentando en %ds...",
                        attempt, _MAX_CONNECT_RETRIES, e, wait,
                    )
                    time.sleep(wait)
                else:
                    raise ConnectionError(
                        f"No se pudo conectar a ChromaDB en {self._host}:{self._port} "
                        f"después de {_MAX_CONNECT_RETRIES} intentos"
                    ) from e

    def add_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """Agrega chunks con sus embeddings a la colección en batches."""
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks ({len(chunks)}) y embeddings ({len(embeddings)}) deben tener el mismo tamaño"
            )

        batch_size = 100
        total_added = 0
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            self._collection.add(
                ids=[c.id for c in batch_chunks],
                embeddings=batch_embeddings,
                documents=[c.content for c in batch_chunks],
                metadatas=[c.metadata for c in batch_chunks],
            )
            total_added += len(batch_chunks)

        logger.info("Agregados %d chunks al vector store", total_added)

    def search(self, query_embedding: List[float], k: int = 5) -> List[Chunk]:
        """Busca los k chunks más similares al query."""
        collection_count = self._collection.count()
        if collection_count == 0:
            return []

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection_count),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results and results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][idx] if results.get("metadatas") else {}
                chunk = Chunk(
                    id=results["ids"][0][idx],
                    document_id=metadata.get("document_id", ""),
                    content=results["documents"][0][idx],
                    metadata=metadata,
                )
                chunks.append(chunk)

        return chunks

    def count(self) -> int:
        """Retorna la cantidad de chunks indexados."""
        return self._collection.count()

    def delete_collection(self) -> None:
        """Elimina la colección completa y la recrea vacía."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Colección '%s' eliminada y recreada", self._collection_name)
