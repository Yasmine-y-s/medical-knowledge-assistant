from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list | None
    prompt_tokens: int
    completion_tokens: int


class LLM(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], tools: Optional[list[dict]] = None, tool_choice=None) -> LLMResponse:
        """Send messages (and optional tool schemas) to a language model, return its response."""


class VectorStore(ABC):
    @abstractmethod
    def similarity_search(self, embedding: list[float], top_k: int = 4) -> list[dict]:
        """Return the top_k most similar stored chunks to the given embedding."""
