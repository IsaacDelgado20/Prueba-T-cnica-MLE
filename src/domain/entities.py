"""
Entidades del dominio - Capa central de la arquitectura hexagonal.
No depende de ninguna capa externa.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid


def _utcnow() -> datetime:
    """Genera datetime UTC con timezone-aware (evita datetime.utcnow deprecado)."""
    return datetime.now(timezone.utc)


class Role(str, Enum):
    """Roles válidos para mensajes de conversación."""
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Chunk:
    """Fragmento de texto de un documento, listo para ser vectorizado (Value Object)."""

    id: str
    document_id: str
    content: str
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("Chunk content no puede estar vacío")

    @staticmethod
    def create(document_id: str, content: str, metadata: Optional[Dict] = None) -> "Chunk":
        return Chunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=content.strip(),
            metadata=metadata or {},
        )


@dataclass
class Document:
    """Documento web scrapeado con contenido crudo y limpio."""

    id: str
    url: str
    title: str
    raw_content: str
    clean_content: str
    chunks: List[Chunk] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self):
        if not self.url:
            raise ValueError("Document URL no puede estar vacía")

    @staticmethod
    def create(url: str, title: str, raw_content: str, clean_content: str) -> "Document":
        return Document(
            id=str(uuid.uuid4()),
            url=url,
            title=title or url,
            raw_content=raw_content,
            clean_content=clean_content,
        )

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


@dataclass(frozen=True)
class Message:
    """Mensaje en una conversación (Value Object)."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=_utcnow)
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        valid_roles = {r.value for r in Role}
        if self.role not in valid_roles:
            raise ValueError(f"Role debe ser uno de {valid_roles}, recibido: '{self.role}'")
        if not self.content or not self.content.strip():
            raise ValueError("Message content no puede estar vacío")


@dataclass
class Conversation:
    """Conversación con historial de mensajes (Aggregate Root)."""

    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @staticmethod
    def create(conversation_id: Optional[str] = None) -> "Conversation":
        return Conversation(
            id=conversation_id or str(uuid.uuid4()),
            messages=[],
        )

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> Message:
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.updated_at = _utcnow()
        return msg

    def get_recent_messages(self, n: int) -> List[Message]:
        """Obtiene los N mensajes más recientes."""
        if n <= 0:
            return list(self.messages)
        return self.messages[-n:]

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def is_empty(self) -> bool:
        return len(self.messages) == 0
