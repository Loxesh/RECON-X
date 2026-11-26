
from app.llm.providers.base import BaseLLMProvider
from app.llm.schemas import LLMRequest, LLMResponse


class MockProvider(BaseLLMProvider):
    """Deterministic offline provider for development and testing."""

    provider_name = "mock"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        last_message = request.messages[-1].content

        return LLMResponse(
            content=f"Mock response received for: {last_message[:200]}",
            provider=self.provider_name,
            model="mock-v1",
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
        )
