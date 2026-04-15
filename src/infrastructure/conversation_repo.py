"""
Repositorio SQLite para conversaciones - Implementa ConversationRepository.
Repository Pattern: abstrae la persistencia de conversaciones.
Usa WAL mode para mejor concurrencia y context manager para conexiones.
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, List, Optional

from src.domain.entities import Conversation, Message
from src.domain.ports import ConversationRepository

logger = logging.getLogger(__name__)


class SQLiteConversationRepository(ConversationRepository):
    """Repositorio de conversaciones usando SQLite (Repository Pattern)."""

    def __init__(self, db_path: str = "./data/conversations.db"):
        self._db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager para conexiones SQLite thread-safe."""
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id)
                """
            )

    def save(self, conversation: Conversation) -> None:
        """Guarda o actualiza una conversación completa."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, created_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (
                    conversation.id,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                ),
            )

            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation.id,),
            )

            if conversation.messages:
                conn.executemany(
                    """
                    INSERT INTO messages
                    (conversation_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            conversation.id,
                            msg.role,
                            msg.content,
                            msg.timestamp.isoformat(),
                            json.dumps(msg.metadata, ensure_ascii=False),
                        )
                        for msg in conversation.messages
                    ],
                )

    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Obtiene una conversación por su ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()

            if not row:
                return None

            conversation = Conversation(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

            messages = conn.execute(
                """
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                """,
                (conversation_id,),
            ).fetchall()

            for msg_row in messages:
                conversation.messages.append(
                    Message(
                        role=msg_row["role"],
                        content=msg_row["content"],
                        timestamp=datetime.fromisoformat(msg_row["timestamp"]),
                        metadata=json.loads(msg_row["metadata"]),
                    )
                )

            return conversation

    def list_all(self) -> List[Conversation]:
        """Lista todas las conversaciones con sus mensajes."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM conversations ORDER BY updated_at DESC"
            ).fetchall()

        # Obtener cada conversación individualmente (incluye mensajes)
        conversations = []
        for row in rows:
            conv = self.get(row["id"])
            if conv:
                conversations.append(conv)

        return conversations

    def delete(self, conversation_id: str) -> None:
        """Elimina una conversación y sus mensajes (CASCADE)."""
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
