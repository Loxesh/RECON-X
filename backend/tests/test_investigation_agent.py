
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.agents.base_agent import AgentContext
from app.agents.investigation_agent.agent import InvestigationAgent
from app.agents.investigation_agent.schemas import (
    InvestigationAgentOutput,
    InvestigationEvidence,
)
from app.agents.tool_registry import ToolRegistry
from app.llm.prompt_registry import create_default_prompt_registry
from app.llm.schemas import LLMResponse, LLMUsageContext


@pytest.fixture
def context():
    return AgentContext(
        org_id="org-1",
        job_id="job-1",
        workflow_run_id="workflow-1",
        correlation_id="correlation-1",
    )


@pytest.fixture
def evidence():
    return [
        InvestigationEvidence(
            record_id="TXN001",
            record_type="transaction",
            summary="Bank transaction amount is 100 INR.",
            details={"amount": "100.00"},
        ),
        InvestigationEvidence(
            record_id="LEDGER001",
            record_type="transaction",
            summary="Ledger transaction amount is 105 INR.",
            details={"amount": "105.00"},
        ),
    ]


@pytest.fixture
def usage_context():
    return LLMUsageContext(
        org_id="org-1",
        job_id="job-1",
        agent_name="investigation_agent",
        task="exception_investigation",
        tier="standard",
        correlation_id="correlation-1",
        estimated_cost="0",
        price_version="test",
        currency="INR",
    )


@pytest.fixture
def llm_response():
    return LLMResponse(
        content=json.dumps({
            "explanation": "The bank and ledger amounts differ.",
            "claims": [
                {
                    "claim": "The bank amount is 100 INR.",
                    "evidence_record_ids": ["TXN001"],
                },
                {
                    "claim": "The ledger amount is 105 INR.",
                    "evidence_record_ids": ["LEDGER001"],
                },
            ],
            "cited_record_ids": ["TXN001", "LEDGER001"],
            "recommended_actions": ["Request human review."],
        }),
        provider="mock",
        model="mock-model",
        input_tokens=100,
        output_tokens=80,
        latency_ms=25,
        fallback_used=False,
    )


@pytest.fixture
def agent(usage_context, llm_response):
    gateway = AsyncMock()
    gateway.generate.return_value = llm_response

    instance = InvestigationAgent(
        tool_registry=ToolRegistry(),
        llm_gateway=gateway,
        usage_context_factory=lambda context: usage_context,
        prompt_registry_instance=create_default_prompt_registry(),
    )

    return instance, gateway


@pytest.mark.asyncio
async def test_investigation_agent_executes_with_evidence(
    agent,
    context,
    evidence,
):
    investigation_agent, gateway = agent

    result = await investigation_agent.run(
        payload={
            "exception_id": "EXC001",
            "task_context": "Investigate the amount discrepancy.",
            "evidence": [
                item.model_dump() for item in evidence
            ],
        },
        context=context,
    )

    assert result.status.value == "SUCCESS"
    assert result.output is not None
    assert result.output.exception_id == "EXC001"
    assert set(result.output.cited_record_ids) == {
        "TXN001",
        "LEDGER001",
    }

    gateway.generate.assert_awaited_once()

    request = gateway.generate.await_args.args[0]
    assert request.system_policy
    assert "TXN001" in request.messages[0].content


@pytest.mark.asyncio
async def test_investigation_agent_rejects_duplicate_evidence_ids(
    agent,
    context,
    evidence,
):
    investigation_agent, gateway = agent

    duplicate_evidence = [
        evidence[0],
        evidence[0],
    ]

    result = await investigation_agent.run(
        payload={
            "exception_id": "EXC001",
            "task_context": "Investigate discrepancy.",
            "evidence": [
                item.model_dump() for item in duplicate_evidence
            ],
        },
        context=context,
    )

    assert result.status.value == "FAILED"
    gateway.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_investigation_agent_rejects_tenant_context_mismatch(
    context,
    evidence,
    llm_response,
):
    gateway = AsyncMock()
    gateway.generate.return_value = llm_response

    wrong_usage_context = LLMUsageContext(
        org_id="different-org",
        job_id=context.job_id,
        agent_name="investigation_agent",
        task="exception_investigation",
        tier="standard",
        correlation_id=context.correlation_id,
        estimated_cost="0",
        price_version="test",
        currency="INR",
    )

    investigation_agent = InvestigationAgent(
        tool_registry=ToolRegistry(),
        llm_gateway=gateway,
        usage_context_factory=lambda _: wrong_usage_context,
        prompt_registry_instance=create_default_prompt_registry(),
    )

    result = await investigation_agent.run(
        payload={
            "exception_id": "EXC001",
            "task_context": "Investigate discrepancy.",
            "evidence": [
                item.model_dump() for item in evidence
            ],
        },
        context=context,
    )

    assert result.status.value == "FAILED"
    gateway.generate.assert_not_awaited()


def test_investigation_evidence_requires_record_identity():
    evidence = InvestigationEvidence(
        record_id="exception-123",
        record_type="exception",
        summary="Amount discrepancy detected.",
    )

    assert evidence.record_id == "exception-123"


def test_investigation_output_rejects_match_decisions():
    payload = {
        "exception_id": "exception-123",
        "explanation": "The supplied evidence indicates an amount discrepancy.",
        "claims": [
            {
                "claim": "The transaction amounts differ.",
                "evidence_record_ids": ["transaction-1"],
            }
        ],
        "cited_record_ids": ["transaction-1"],
        "recommended_actions": ["Request human review."],
        "provider": "mock",
        "model": "mock-model",
        "input_tokens": 10,
        "output_tokens": 20,
        "latency_ms": 5,
        "fallback_used": False,
        "match_status": "CONFIRMED_AUTO",
    }

    with pytest.raises(ValidationError):
        InvestigationAgentOutput.model_validate(payload)


def test_investigation_output_rejects_exception_status_changes():
    payload = {
        "exception_id": "exception-123",
        "explanation": "Evidence requires further review.",
        "claims": [
            {
                "claim": "Evidence is available.",
                "evidence_record_ids": ["record-1"],
            }
        ],
        "cited_record_ids": ["record-1"],
        "recommended_actions": [],
        "provider": "mock",
        "model": "mock-model",
        "input_tokens": 10,
        "output_tokens": 20,
        "latency_ms": 5,
        "fallback_used": False,
        "exception_status": "CLOSED",
    }

    with pytest.raises(ValidationError):
        InvestigationAgentOutput.model_validate(payload)
