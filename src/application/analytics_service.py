"""
Servicio de Analíticas - Capa de aplicación.
Extrae métricas y valores de impacto del histórico de conversaciones.
"""

import logging
import re
from collections import Counter
from statistics import mean
from typing import Dict, List

from src.domain.ports import ConversationRepository

logger = logging.getLogger(__name__)

# Patrón para tokenización simple: solo palabras alfanuméricas con tildes
_WORD_PATTERN = re.compile(r"[a-záéíóúüñ]{3,}", re.IGNORECASE)

# Stop words en español e inglés para filtrar del análisis de keywords
_STOP_WORDS: frozenset = frozenset({
    "de", "la", "el", "en", "un", "una", "los", "las", "y", "a", "que",
    "es", "se", "por", "para", "con", "del", "al", "como", "más", "pero",
    "sus", "le", "ya", "o", "fue", "este", "ha", "sí", "no", "son", "su",
    "me", "mi", "qué", "cuál", "cómo", "tiene", "hay", "sobre", "puede",
    "puedo", "quiero", "cuáles", "the", "is", "of", "and", "to", "in",
    "it", "what", "how", "do", "does", "are", "was", "been", "be", "have",
    "has", "had", "will", "would", "could", "should", "this", "that",
    "these", "those", "tengo", "ser", "hola", "gracias", "bien", "muy",
    "todo", "esta", "esto", "eso", "también", "desde", "donde", "cuando",
    "sin", "porque", "entre", "hasta", "cada", "otro", "otra", "otros",
})

_EMPTY_METRICS: Dict = {
    "total_conversations": 0,
    "total_messages": 0,
    "avg_messages_per_conversation": 0.0,
    "total_user_messages": 0,
    "total_assistant_messages": 0,
    "avg_response_time_s": 0.0,
    "top_keywords": [],
    "conversations_by_date": {},
    "avg_user_message_length": 0,
    "avg_assistant_message_length": 0,
}


class AnalyticsService:
    """Servicio de aplicación para analítica de conversaciones."""

    def __init__(self, conversation_repo: ConversationRepository):
        self._conversation_repo = conversation_repo

    def get_metrics(self) -> Dict:
        """Calcula métricas generales del historial de conversaciones."""
        conversations = self._conversation_repo.list_all()

        if not conversations:
            return dict(_EMPTY_METRICS)

        user_msg_lengths: List[int] = []
        assistant_msg_lengths: List[int] = []
        response_times: List[float] = []
        all_user_words: List[str] = []
        conversations_by_date: Counter = Counter()

        for conv in conversations:
            date_key = conv.created_at.strftime("%Y-%m-%d")
            conversations_by_date[date_key] += 1

            for msg in conv.messages:
                if msg.role == "user":
                    user_msg_lengths.append(len(msg.content))
                    words = _WORD_PATTERN.findall(msg.content.lower())
                    all_user_words.extend(
                        w for w in words if w not in _STOP_WORDS
                    )

                elif msg.role == "assistant":
                    assistant_msg_lengths.append(len(msg.content))
                    rt = msg.metadata.get("response_time_s")
                    if rt is not None:
                        response_times.append(float(rt))

        total_msgs = len(user_msg_lengths) + len(assistant_msg_lengths)
        word_freq = Counter(all_user_words)

        return {
            "total_conversations": len(conversations),
            "total_messages": total_msgs,
            "avg_messages_per_conversation": round(
                total_msgs / len(conversations), 1
            ),
            "total_user_messages": len(user_msg_lengths),
            "total_assistant_messages": len(assistant_msg_lengths),
            "avg_response_time_s": round(mean(response_times), 2)
            if response_times
            else 0.0,
            "top_keywords": word_freq.most_common(20),
            "conversations_by_date": dict(sorted(conversations_by_date.items())),
            "avg_user_message_length": round(mean(user_msg_lengths))
            if user_msg_lengths
            else 0,
            "avg_assistant_message_length": round(mean(assistant_msg_lengths))
            if assistant_msg_lengths
            else 0,
        }

    def get_conversation_details(self) -> List[Dict]:
        """Obtiene información detallada de cada conversación."""
        conversations = self._conversation_repo.list_all()
        details: List[Dict] = []

        for conv in conversations:
            user_msgs = [m for m in conv.messages if m.role == "user"]
            assistant_msgs = [m for m in conv.messages if m.role == "assistant"]

            response_times = [
                float(m.metadata.get("response_time_s", 0))
                for m in assistant_msgs
                if m.metadata.get("response_time_s")
            ]

            details.append({
                "conversation_id": conv.id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "total_messages": len(conv.messages),
                "user_messages": len(user_msgs),
                "assistant_messages": len(assistant_msgs),
                "avg_response_time_s": round(mean(response_times), 2)
                if response_times
                else 0.0,
                "first_question": user_msgs[0].content[:100] if user_msgs else "",
            })

        return details
