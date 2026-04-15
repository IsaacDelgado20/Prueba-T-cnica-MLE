"""
Adaptadores de LLM - Implementan LLMPort.
Strategy Pattern: OllamaLLMAdapter y OpenAILLMAdapter son intercambiables.
Ambos usan la API compatible con OpenAI. DRY: lógica común en _BaseLLMAdapter.
"""

import logging
from typing import Optional

from openai import OpenAI

from src.domain.ports import LLMPort

logger = logging.getLogger(__name__)


class _BaseLLMAdapter(LLMPort):
    """Clase base con lógica común para adaptadores LLM (Template Method)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        system_prompt: str = "Eres un asistente virtual de BBVA Colombia. Responde en español.",
    ):
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._default_system_prompt = system_prompt

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Genera respuesta usando la API compatible con OpenAI."""
        effective_system = system_prompt or self._default_system_prompt
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": effective_system},
                    {"role": "user", "content": prompt},
                ],
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("LLM retornó respuesta vacía")
            return content
        except Exception as e:
            logger.error("Error en generación LLM (%s): %s", self._model, e)
            raise RuntimeError(f"Error generando respuesta del LLM: {e}") from e


class OllamaLLMAdapter(_BaseLLMAdapter):
    """Adaptador Ollama via API compatible con OpenAI (Strategy Pattern)."""

    def __init__(
        self,
        base_url: str = "http://ollama:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        system_prompt: str = "Eres un asistente virtual de BBVA Colombia. Responde en español.",
    ):
        super().__init__(base_url, model, api_key, temperature, max_tokens, system_prompt)
        logger.info("Ollama LLM configurado: modelo=%s, url=%s", model, base_url)


class OpenAILLMAdapter(_BaseLLMAdapter):
    """Adaptador OpenAI/Groq compatible (Strategy Pattern)."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        api_key: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
        system_prompt: str = "Eres un asistente virtual de BBVA Colombia. Responde en español.",
    ):
        super().__init__(base_url, model, api_key, temperature, max_tokens, system_prompt)
        logger.info("OpenAI-compatible LLM configurado: modelo=%s", model)
