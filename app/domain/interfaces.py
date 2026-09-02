from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: Optional[list]
    prompt_tokens: int
    completion_tokens: int


class LLM(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], tools: list[dict] = None, tool_choice=None) -> LLMResponse:
        """Send messages (and optional tool schemas) to a language model, return its response."""
        pass


class VectorStore(ABC):
    @abstractmethod
    def similarity_search(self, embedding: list[float], top_k: int = 4) -> list[dict]:
        """Return the top_k most similar stored chunks to the given embedding."""
        pass