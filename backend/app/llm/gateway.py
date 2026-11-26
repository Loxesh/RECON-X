
import logging
import time
from typing import Sequence

from app.core.config import Settings, settings
from app.llm.exceptions import GatewayError, ProviderError
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.local import LocalProvider
from app.llm.providers.mock import MockProvider
from app.llm.providers.openai_compatible import OpenAICompatibleProvider
from app.llm.schemas import LLMRequest, LLMResponse, LLMUsageContext
from app.llm.usage import LLMUsageRecorder


logger = logging.getLogger(__name__)


class LLMGateway:
    """Central gateway for provider selection, fallback and usage recording."""

    def __init__(
        self,
        providers: dict[str, BaseLLMProvider],
        primary_provider: str,
        fallback_providers: Sequence[str] = (),
        usage_recorder: LLMUsageRecorder | None = None,
    ) -> None:
        if primary_provider not in providers:
            raise ValueError("Primary LLM provider is not registered.")

        for provider_name in fallback_providers:
            if provider_name not in providers:
                raise ValueError("A fallback LLM provider is not registered.")

        self.providers = providers
        self.primary_provider = primary_provider
        self.fallback_providers = tuple(
            name for name in fallback_providers
            if name != primary_provider
        )
        self.usage_recorder = usage_recorder

    async def generate(
        self,
        request: LLMRequest,
        usage_context: LLMUsageContext,
    ) -> LLMResponse:
        provider_order = (
            self.primary_provider,
            *self.fallback_providers,
        )

        last_error: ProviderError | None = None

        for index, provider_name in enumerate(provider_order):
            provider = self.providers[provider_name]
            started_at = time.perf_counter()

            try:
                response = await provider.generate(request)

                latency_ms = max(
                    0,
                    int((time.perf_counter() - started_at) * 1000),
                )

                response = response.model_copy(
                    update={
                        "latency_ms": latency_ms,
                        "fallback_used": index > 0,
                    }
                )

                if self.usage_recorder is not None:
                    try:
                        self.usage_recorder.record(
                            usage_context,
                            response,
                        )
                    except Exception:
                        logger.error(
                            "LLM usage recording failed. "
                            "Correlation ID: %s",
                            usage_context.correlation_id,
                        )

                return response

            except ProviderError as exc:
                last_error = exc

                logger.warning(
                    "LLM provider attempt failed. Provider: %s, "
                    "Code: %s, Correlation ID: %s",
                    provider_name,
                    exc.code,
                    usage_context.correlation_id,
                )

                if not exc.retryable:
                    break

        raise GatewayError(
            "No configured LLM provider could complete the request."
        ) from None


def create_llm_gateway(
    configuration: Settings = settings,
    usage_recorder: LLMUsageRecorder | None = None,
) -> LLMGateway:
    """Build the configured gateway without exposing provider credentials."""

    providers: dict[str, BaseLLMProvider] = {}

    providers["mock"] = MockProvider()

    if configuration.gemini_api_key:
        providers["gemini"] = GeminiProvider(
            api_key=configuration.gemini_api_key.get_secret_value(),
            model=configuration.gemini_model,
            timeout_seconds=configuration.llm_timeout_seconds,
        )

    if configuration.openai_compat_api_key:
        providers["openai_compatible"] = OpenAICompatibleProvider(
            api_key=configuration.openai_compat_api_key.get_secret_value(),
            base_url=configuration.openai_compat_base_url,
            model=configuration.openai_compat_model,
            timeout_seconds=configuration.llm_timeout_seconds,
        )

    providers["local"] = LocalProvider(
        base_url=configuration.local_llm_base_url,
        model=configuration.local_llm_model,
        timeout_seconds=configuration.llm_timeout_seconds,
    )

    primary = configuration.llm_provider.strip().lower()
    fallbacks = configuration.llm_fallback_provider_list

    if primary not in providers:
        raise ValueError(
            f"Configured LLM provider '{primary}' is unavailable. "
            "Check provider configuration and credentials."
        )

    for name in fallbacks:
        if name not in providers:
            raise ValueError(
                f"Configured fallback provider '{name}' is unavailable."
            )

    return LLMGateway(
        providers=providers,
        primary_provider=primary,
        fallback_providers=fallbacks,
        usage_recorder=usage_recorder,
    )
