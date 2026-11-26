
from app.llm.providers.openai_compatible import OpenAICompatibleProvider


class LocalProvider(OpenAICompatibleProvider):
    provider_name = "local"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            api_key="",
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            provider_name=self.provider_name,
        )
