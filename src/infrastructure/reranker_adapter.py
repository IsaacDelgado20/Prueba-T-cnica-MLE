"""
Adaptador Cross-Encoder para reranking - Implementa RerankerPort.
Mejora la relevancia de los resultados recuperados antes de pasarlos al LLM.
"""

import logging
from typing import List

from sentence_transformers import CrossEncoder

from src.domain.entities import Chunk
from src.domain.ports import RerankerPort

logger = logging.getLogger(__name__)


class CrossEncoderReranker(RerankerPort):
    """Reranker basado en Cross-Encoder para mejorar la relevancia."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        logger.info("Cargando modelo de reranking: %s", model_name)
        self._model = CrossEncoder(model_name)
        logger.info("Modelo de reranking cargado correctamente")

    def rerank(self, query: str, chunks: List[Chunk], top_k: int = 3) -> List[Chunk]:
        """Reordena los chunks por relevancia usando cross-encoder."""
        if not chunks:
            return []

        if top_k <= 0:
            return []

        try:
            pairs = [(query, chunk.content) for chunk in chunks]
            scores = self._model.predict(pairs)

            scored_chunks = sorted(
                zip(chunks, scores), key=lambda x: float(x[1]), reverse=True
            )

            reranked = [chunk for chunk, _ in scored_chunks[:top_k]]
            logger.debug(
                "Reranked %d chunks -> top %d (best score: %.3f)",
                len(chunks), len(reranked),
                float(scored_chunks[0][1]) if scored_chunks else 0,
            )
            return reranked

        except Exception as e:
            logger.error("Error en reranking, retornando chunks sin reordenar: %s", e)
            return chunks[:top_k]
