
import httpx

from app.llm.exceptions import ProviderError
from app.llm.providers.base import BaseLLMProvider
from app.llm.schemas import LLMRequest, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_name = "openai_compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 20.0,
        provider_name: str = "openai_compatible",
    ) -> None:
        if not base_url:
            raise ValueError("Provider base URL is required.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.provider_name = provider_name

    async def generate(self, request: LLMRequest) -> LLMResponse:
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                item.model_dump() for item in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            if response.status_code >= 400:
                raise ProviderError(
                    self.provider_name,
                    code="http_error",
                    retryable=response.status_code in (408, 429, 500, 502, 503, 504),
                )

            data = response.json()
            choices = data.get("choices") or []

            if not choices:
                raise ProviderError(
                    self.provider_name,
                    code="empty_response",
                )

            content = choices[0].get("message", {}).get("content")

            if not isinstance(content, str) or not content:
                raise ProviderError(
                    self.provider_name,
                    code="invalid_response",
                )

            usage = data.get("usage") or {}

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=self.model,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
            )

        except ProviderError:
            raise
        except httpx.TimeoutException:
            raise ProviderError(
                self.provider_name,
                code="timeout",
                retryable=True,
            ) from None
        except httpx.RequestError:
            raise ProviderError(
                self.provider_name,
                code="connection_error",
                retryable=True,
            ) from None
        except (ValueError, KeyError, TypeError):
            raise ProviderError(
                self.provider_name,
                code="invalid_response",
            ) from None
