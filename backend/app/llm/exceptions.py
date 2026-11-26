
class LLMError(Exception):
    """Base exception for sanitized LLM gateway errors."""


class ProviderError(LLMError):
    """Safe provider failure that does not expose response bodies or secrets."""

    def __init__(
        self,
        provider: str,
        code: str = "provider_error",
        retryable: bool = False,
    ) -> None:
        self.provider = provider
        self.code = code
        self.retryable = retryable
        super().__init__(f"LLM provider '{provider}' failed ({code}).")


class GatewayError(LLMError):
    """Raised when no configured provider can complete a request."""
