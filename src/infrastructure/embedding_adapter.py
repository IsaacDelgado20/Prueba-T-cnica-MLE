"""
Adaptador de Sentence Transformers para embeddings - Implementa EmbeddingPort.
Parte del Strategy Pattern: intercambiable con otros proveedores de embeddings.
"""

import logging
from typing import List

from sentence_transformers import SentenceTransformer

from src.domain.ports import EmbeddingPort

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding(EmbeddingPort):
    """Adaptador de embeddings usando Sentence Transformers (local, gratuito)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info("Cargando modelo de embeddings: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info(
            "Modelo de embeddings cargado (dimensión: %d)", self._dimension
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para una lista de textos."""
        if not texts:
            return []
        embeddings = self._model.encode(
            texts, show_progress_bar=False, normalize_embeddings=True
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """Retorna la dimensión de los embeddings generados."""
        return self._dimension
