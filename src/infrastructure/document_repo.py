"""
Repositorio de documentos basado en archivos - Implementa DocumentRepository.
Repository Pattern: almacena documentos crudos (HTML) y limpios (TXT) en el filesystem.
Usa pathlib para manejo cross-platform de rutas.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from src.domain.entities import Document
from src.domain.ports import DocumentRepository

logger = logging.getLogger(__name__)


class FileDocumentRepository(DocumentRepository):
    """Repositorio de documentos usando el sistema de archivos (Repository Pattern)."""

    def __init__(self, data_dir: str = "./data"):
        self._raw_dir = Path(data_dir) / "raw"
        self._clean_dir = Path(data_dir) / "clean"
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._clean_dir.mkdir(parents=True, exist_ok=True)

    def save_raw(self, document: Document) -> None:
        """Guarda el contenido crudo (HTML) del documento."""
        html_path = self._raw_dir / f"{document.id}.html"
        html_path.write_text(document.raw_content, encoding="utf-8")

        meta_path = self._raw_dir / f"{document.id}.json"
        meta_path.write_text(
            json.dumps(
                {
                    "id": document.id,
                    "url": document.url,
                    "title": document.title,
                    "scraped_at": document.scraped_at.isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.debug("Documento crudo guardado: %s", document.url)

    def save_clean(self, document: Document) -> None:
        """Guarda el contenido limpio (texto) del documento."""
        txt_path = self._clean_dir / f"{document.id}.txt"
        txt_path.write_text(document.clean_content, encoding="utf-8")

        meta_path = self._clean_dir / f"{document.id}.json"
        meta_path.write_text(
            json.dumps(
                {
                    "id": document.id,
                    "url": document.url,
                    "title": document.title,
                    "scraped_at": document.scraped_at.isoformat(),
                    "content_length": len(document.clean_content),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.debug("Documento limpio guardado: %s", document.url)

    def list_documents(self) -> List[Dict]:
        """Lista los metadatos de todos los documentos limpios almacenados."""
        docs = []
        for meta_file in sorted(self._clean_dir.glob("*.json")):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                docs.append(data)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Error leyendo metadata %s: %s", meta_file, e)
        return docs
