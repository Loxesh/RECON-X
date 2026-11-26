
import asyncio
from decimal import Decimal

import pytest

from app.llm.exceptions import GatewayError, ProviderError
from app.llm.gateway import LLMGateway
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.mock import MockProvider
from app.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMUsageContext,
)


def make_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(role="user", content="Synthetic exception context"),
        ]
    )


def make_usage_context() -> LLMUsageContext:
    return LLMUsageContext(
        org_id="ORG_TEST",
        job_id="JOB_TEST",
        agent_name="investigation_agent",
        task="investigation",
        tier="standard",
        correlation_id="CORR_TEST",
        estimated_cost=Decimal("0.00"),
        price_version="test-unpriced-v1",
    )


class FailingProvider(BaseLLMProvider):
    provider_name = "failing"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        raise ProviderError(
            self.provider_name,
            code="temporary_failure",
            retryable=True,
        )


class PermanentFailureProvider(BaseLLMProvider):
    provider_name = "permanent"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        raise ProviderError(
            self.provider_name,
            code="invalid_request",
            retryable=False,
        )


def test_mock_provider_returns_response():
    response = asyncio.run(MockProvider().generate(make_request()))

    assert response.provider == "mock"
    assert response.model == "mock-v1"
    assert "Synthetic exception context" in response.content


def test_gateway_uses_primary_provider():
    gateway = LLMGateway(
        providers={"mock": MockProvider()},
        primary_provider="mock",
    )

    response = asyncio.run(
        gateway.generate(make_request(), make_usage_context())
    )

    assert response.provider == "mock"
    assert response.fallback_used is False


def test_gateway_uses_fallback_after_retryable_error():
    gateway = LLMGateway(
        providers={
            "failing": FailingProvider(),
            "mock": MockProvider(),
        },
        primary_provider="failing",
        fallback_providers=["mock"],
    )

    response = asyncio.run(
        gateway.generate(make_request(), make_usage_context())
    )

    assert response.provider == "mock"
    assert response.fallback_used is True


def test_gateway_does_not_fallback_after_permanent_error():
    gateway = LLMGateway(
        providers={
            "permanent": PermanentFailureProvider(),
            "mock": MockProvider(),
        },
        primary_provider="permanent",
        fallback_providers=["mock"],
    )

    with pytest.raises(GatewayError):
        asyncio.run(
            gateway.generate(make_request(), make_usage_context())
        )


def test_gateway_raises_when_all_providers_fail():
    gateway = LLMGateway(
        providers={"failing": FailingProvider()},
        primary_provider="failing",
    )

    with pytest.raises(GatewayError):
        asyncio.run(
            gateway.generate(make_request(), make_usage_context())
        )


def test_usage_context_rejects_negative_cost():
    with pytest.raises(ValueError):
        LLMUsageContext(
            org_id="ORG_TEST",
            job_id="JOB_TEST",
            agent_name="test_agent",
            task="test",
            correlation_id="CORR_TEST",
            estimated_cost=Decimal("-1.00"),
            price_version="test-v1",
        )


def test_usage_context_rejects_float_cost():
    with pytest.raises(ValueError):
        LLMUsageContext(
            org_id="ORG_TEST",
            job_id="JOB_TEST",
            agent_name="test_agent",
            task="test",
            correlation_id="CORR_TEST",
            estimated_cost=0.25,
            price_version="test-v1",
        )


def test_gateway_rejects_missing_primary_provider():
    with pytest.raises(ValueError):
        LLMGateway(
            providers={"mock": MockProvider()},
            primary_provider="missing",
        )
