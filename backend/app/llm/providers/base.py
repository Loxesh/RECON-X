
from abc import ABC, abstractmethod

from app.llm.schemas import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """Contract implemented by every LLM provider adapter."""

    provider_name: str

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using this provider."""
        raise NotImplementedError
