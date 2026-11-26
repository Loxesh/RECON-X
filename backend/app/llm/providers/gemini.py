
import httpx

from app.llm.exceptions import ProviderError
from app.llm.providers.base import BaseLLMProvider
from app.llm.schemas import LLMRequest, LLMResponse


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required.")

        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: LLMRequest) -> LLMResponse:
        system_messages = [
            item.content for item in request.messages
            if item.role == "system"
        ]
        contents = [
            {
                "role": "model" if item.role == "assistant" else "user",
                "parts": [{"text": item.content}],
            }
            for item in request.messages
            if item.role != "system"
        ]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }

        if system_messages:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n".join(system_messages)}]
            }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self.model}:generateContent"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                )

            if response.status_code >= 400:
                raise ProviderError(
                    self.provider_name,
                    code="http_error",
                    retryable=response.status_code in (408, 429, 500, 502, 503, 504),
                )

            data = response.json()
            candidates = data.get("candidates") or []
            parts = (
                candidates[0].get("content", {}).get("parts", [])
                if candidates else []
            )
            content = "".join(
                part.get("text", "")
                for part in parts
                if isinstance(part, dict)
            )

            if not content:
                raise ProviderError(
                    self.provider_name,
                    code="empty_response",
                )

            usage = data.get("usageMetadata") or {}

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=self.model,
                input_tokens=usage.get("promptTokenCount", 0),
                output_tokens=usage.get("candidatesTokenCount", 0),
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
