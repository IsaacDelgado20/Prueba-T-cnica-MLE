"""
Servicio de Scraping - Capa de aplicación.
Orquesta el scraping, limpieza, chunking, embedding e indexación de documentos.
"""

import logging
from typing import Dict, List

from src.domain.entities import Chunk, Document
from src.domain.ports import (
    DocumentRepository,
    EmbeddingPort,
    ScraperPort,
    VectorStorePort,
)

logger = logging.getLogger(__name__)


class ScrapingService:
    """Servicio de aplicación para scraping y procesamiento de documentos."""

    def __init__(
        self,
        scraper: ScraperPort,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        document_repo: DocumentRepository,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        self._scraper = scraper
        self._embedding = embedding
        self._vector_store = vector_store
        self._document_repo = document_repo
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def scrape_and_index(self, url: str, max_pages: int = 20) -> Dict:
        """
        Pipeline completo: scrape -> almacenar -> chunk -> embed -> indexar.
        Retorna métricas del proceso.
        """
        logger.info("Iniciando scraping de %s (máx %d páginas)", url, max_pages)

        # 1. Scrapear
        documents = self._scraper.scrape(url, max_pages)
        logger.info("Scrapeados %d documentos", len(documents))

        if not documents:
            return {"documents": 0, "chunks": 0, "urls": []}

        total_chunks = 0
        indexed_urls: List[str] = []

        for doc in documents:
            # 2. Almacenar crudo y limpio
            self._document_repo.save_raw(doc)
            self._document_repo.save_clean(doc)

            # 3. Dividir en chunks
            chunks = self._chunk_text(doc)
            doc.chunks = chunks

            if not chunks:
                continue

            # 4. Generar embeddings
            texts = [c.content for c in chunks]
            embeddings = self._embedding.embed(texts)

            # 5. Indexar en vector store
            self._vector_store.add_chunks(chunks, embeddings)
            total_chunks += len(chunks)
            indexed_urls.append(doc.url)

        logger.info(
            "Indexación completada: %d chunks de %d documentos",
            total_chunks, len(documents),
        )

        return {
            "documents": len(documents),
            "chunks": total_chunks,
            "urls": indexed_urls,
        }

    def _chunk_text(self, document: Document) -> List[Chunk]:
        """
        Divide el texto del documento en chunks.
        Estrategia: agrupar párrafos hasta el tamaño de chunk,
        luego dividir párrafos largos con overlap.
        """
        text = document.clean_content
        if not text.strip():
            return []

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        raw_chunks: List[str] = []
        current_chunk = ""

        for para in paragraphs:
            candidate = f"{current_chunk}\n\n{para}".strip() if current_chunk else para

            if len(candidate) <= self._chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    raw_chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            raw_chunks.append(current_chunk)

        # Dividir chunks que excedan el tamaño con overlap
        final_chunks: List[Chunk] = []
        base_metadata = {"url": document.url, "title": document.title}

        for text_block in raw_chunks:
            if len(text_block) <= self._chunk_size:
                final_chunks.append(
                    Chunk.create(
                        document_id=document.id,
                        content=text_block,
                        metadata=base_metadata,
                    )
                )
            else:
                step = max(1, self._chunk_size - self._chunk_overlap)
                for i in range(0, len(text_block), step):
                    piece = text_block[i : i + self._chunk_size].strip()
                    if piece:
                        final_chunks.append(
                            Chunk.create(
                                document_id=document.id,
                                content=piece,
                                metadata=base_metadata,
                            )
                        )

        return final_chunks

    def get_index_count(self) -> int:
        """Retorna la cantidad de chunks indexados."""
        return self._vector_store.count()
