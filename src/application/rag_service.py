"""
Servicio RAG - Capa de aplicación.
Orquesta la recuperación de contexto, reranking y generación de respuestas.
Mantiene el historial de conversación por ID.
"""

import logging
import time
import uuid
from typing import Dict, List, Optional

from src.domain.entities import Chunk, Conversation
from src.domain.ports import (
    ConversationRepository,
    EmbeddingPort,
    LLMPort,
    RerankerPort,
    VectorStorePort,
)

logger = logging.getLogger(__name__)

_RAG_PROMPT_TEMPLATE = """Eres un asistente virtual experto de BBVA Colombia. Tu objetivo es responder preguntas
sobre los productos y servicios de BBVA basándote ÚNICAMENTE en el contexto proporcionado.

REGLAS OBLIGATORIAS:
1. Si la información NO está en el contexto, responde: "No tengo esa información disponible en mi base de conocimiento."
2. Responde SIEMPRE en español, de forma clara, estructurada y concisa.
3. Cita las fuentes [URL] al final de tu respuesta cuando sea posible.
4. Mantén coherencia con el historial de conversación previo.
5. No inventes información ni hagas suposiciones fuera del contexto.

---
CONTEXTO RECUPERADO:
{context}

---
HISTORIAL DE CONVERSACIÓN:
{history}

---
PREGUNTA ACTUAL: {question}

RESPUESTA:"""


class RAGService:
    """Servicio de aplicación para Retrieval-Augmented Generation."""

    def __init__(
        self,
        embedding: EmbeddingPort,
        vector_store: VectorStorePort,
        llm: LLMPort,
        reranker: Optional[RerankerPort],
        conversation_repo: ConversationRepository,
        history_messages: int = 10,
        retrieve_k: int = 10,
        rerank_top_k: int = 3,
    ):
        self._embedding = embedding
        self._vector_store = vector_store
        self._llm = llm
        self._reranker = reranker
        self._conversation_repo = conversation_repo
        self._history_messages = history_messages
        self._retrieve_k = retrieve_k
        self._rerank_top_k = rerank_top_k

    def ask(self, conversation_id: str, question: str) -> Dict:
        """Procesa una pregunta: recupera contexto, reordena, genera respuesta."""
        start_time = time.time()

        # 1. Obtener o crear conversación
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        conversation = self._conversation_repo.get(conversation_id)
        if not conversation:
            conversation = Conversation.create(conversation_id)

        # 2. Agregar mensaje del usuario
        conversation.add_message("user", question)

        # 3. Recuperar chunks relevantes
        query_embedding = self._embedding.embed([question])[0]
        chunks = self._vector_store.search(query_embedding, k=self._retrieve_k)

        # 4. Reranking si está disponible
        if self._reranker and chunks:
            chunks = self._reranker.rerank(question, chunks, top_k=self._rerank_top_k)
        else:
            chunks = chunks[: self._rerank_top_k]

        # 5. Construir prompt con contexto e historial
        prompt = self._build_prompt(conversation, question, chunks)

        # 6. Generar respuesta
        answer = self._llm.generate(prompt)
        elapsed = time.time() - start_time

        # 7. Extraer fuentes únicas
        sources = list({
            c.metadata.get("url", "")
            for c in chunks
            if c.metadata.get("url")
        })

        # 8. Guardar respuesta del asistente con metadata
        conversation.add_message(
            "assistant",
            answer,
            metadata={
                "response_time_s": round(elapsed, 2),
                "chunks_retrieved": len(chunks),
                "sources": sources,
            },
        )
        self._conversation_repo.save(conversation)

        logger.info(
            "RAG respuesta generada en %.2fs (%d chunks, %d fuentes)",
            elapsed, len(chunks), len(sources),
        )

        return {
            "answer": answer,
            "conversation_id": conversation.id,
            "sources": sources,
            "response_time_s": round(elapsed, 2),
            "chunks_used": len(chunks),
        }

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversation_repo.get(conversation_id)

    def list_conversations(self) -> List[Conversation]:
        return self._conversation_repo.list_all()

    def delete_conversation(self, conversation_id: str) -> None:
        self._conversation_repo.delete(conversation_id)

    def _build_prompt(
        self, conversation: Conversation, question: str, chunks: List[Chunk]
    ) -> str:
        """Construye el prompt con contexto RAG e historial de conversación."""
        # Contexto de los chunks recuperados
        if chunks:
            context_parts = []
            for i, c in enumerate(chunks, 1):
                source = c.metadata.get("url", "N/A")
                context_parts.append(f"[Fragmento {i} - Fuente: {source}]\n{c.content}")
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "No se encontró contexto relevante en la base de conocimiento."

        # Historial de conversación reciente (excluyendo el mensaje actual)
        recent = conversation.get_recent_messages(self._history_messages)
        history_lines = []
        for msg in recent[:-1]:  # Sin el último mensaje (es la pregunta actual)
            role_label = "Usuario" if msg.role == "user" else "Asistente"
            history_lines.append(f"{role_label}: {msg.content}")

        history = "\n".join(history_lines) if history_lines else "(Sin historial previo)"

        return _RAG_PROMPT_TEMPLATE.format(
            context=context,
            history=history,
            question=question,
        )
