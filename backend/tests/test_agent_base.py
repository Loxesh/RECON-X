
"""Focused tests for the RECON X agent execution foundation."""

import asyncio

import pytest
from pydantic import BaseModel, ConfigDict, Field

from app.agents.base_agent import (
    AgentContext,
    AgentStatus,
    BaseAgent,
)
from app.agents.tool_registry import (
    ToolPermissionDenied,
    ToolRegistry,
    ToolTimeoutError,
    ToolValidationError,
)


class SampleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int = Field(ge=1)


class SampleOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: int


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int = Field(ge=1)


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: int


class SampleAgent(BaseAgent[SampleInput, SampleOutput]):
    agent_name = "sample_agent"
    input_model = SampleInput
    output_model = SampleOutput

    async def execute(
        self,
        input_data: SampleInput,
        context: AgentContext,
    ) -> SampleOutput:
        return SampleOutput(result=input_data.value * 2)


class SlowAgent(BaseAgent[SampleInput, SampleOutput]):
    agent_name = "slow_agent"
    input_model = SampleInput
    output_model = SampleOutput

    async def execute(
        self,
        input_data: SampleInput,
        context: AgentContext,
    ) -> SampleOutput:
        await asyncio.sleep(0.1)
        return SampleOutput(result=input_data.value)


def make_context() -> AgentContext:
    return AgentContext(
        org_id="org-001",
        job_id="job-001",
        workflow_run_id="workflow-001",
        correlation_id="correlation-001",
    )


def test_agent_success_returns_typed_result():
    agent = SampleAgent(tool_registry=ToolRegistry())

    result = asyncio.run(
        agent.run(
            payload={"value": 5},
            context=make_context(),
        )
    )

    assert result.status == AgentStatus.SUCCESS
    assert result.output == SampleOutput(result=10)
    assert result.duration_ms >= 0
    assert result.error_code is None


def test_agent_rejects_invalid_input():
    agent = SampleAgent(tool_registry=ToolRegistry())

    result = asyncio.run(
        agent.run(
            payload={"value": 0},
            context=make_context(),
        )
    )

    assert result.status == AgentStatus.INVALID_INPUT
    assert result.output is None
    assert result.error_code == "invalid_agent_input"


def test_agent_rejects_unexpected_input_fields():
    agent = SampleAgent(tool_registry=ToolRegistry())

    result = asyncio.run(
        agent.run(
            payload={"value": 5, "unapproved": True},
            context=make_context(),
        )
    )

    assert result.status == AgentStatus.INVALID_INPUT


def test_agent_execution_timeout():
    agent = SlowAgent(
        tool_registry=ToolRegistry(),
        timeout_seconds=0.01,
    )

    result = asyncio.run(
        agent.run(
            payload={"value": 5},
            context=make_context(),
        )
    )

    assert result.status == AgentStatus.TIMED_OUT
    assert result.error_code == "agent_timeout"
    assert result.output is None


def test_tool_is_denied_by_default():
    registry = ToolRegistry()

    async def sample_tool(data: ToolInput) -> ToolOutput:
        return ToolOutput(result=data.value)

    registry.register_tool(
        name="sample.read",
        input_model=ToolInput,
        output_model=ToolOutput,
        handler=sample_tool,
    )

    with pytest.raises(ToolPermissionDenied):
        asyncio.run(
            registry.invoke(
                agent_name="sample_agent",
                tool_name="sample.read",
                payload={"value": 5},
            )
        )


def test_agent_can_use_explicitly_granted_tool():
    registry = ToolRegistry()

    async def sample_tool(data: ToolInput) -> ToolOutput:
        return ToolOutput(result=data.value * 3)

    registry.register_tool(
        name="sample.calculate",
        input_model=ToolInput,
        output_model=ToolOutput,
        handler=sample_tool,
    )

    registry.grant_tool(
        agent_name="sample_agent",
        tool_name="sample.calculate",
    )

    result = asyncio.run(
        registry.invoke(
            agent_name="sample_agent",
            tool_name="sample.calculate",
            payload={"value": 4},
        )
    )

    assert result == ToolOutput(result=12)


def test_tool_rejects_invalid_input():
    registry = ToolRegistry()

    async def sample_tool(data: ToolInput) -> ToolOutput:
        return ToolOutput(result=data.value)

    registry.register_tool(
        name="sample.validate",
        input_model=ToolInput,
        output_model=ToolOutput,
        handler=sample_tool,
    )

    registry.grant_tool(
        agent_name="sample_agent",
        tool_name="sample.validate",
    )

    with pytest.raises(ToolValidationError):
        asyncio.run(
            registry.invoke(
                agent_name="sample_agent",
                tool_name="sample.validate",
                payload={"value": -1},
            )
        )


def test_tool_timeout_is_enforced():
    registry = ToolRegistry()

    async def slow_tool(data: ToolInput) -> ToolOutput:
        await asyncio.sleep(0.1)
        return ToolOutput(result=data.value)

    registry.register_tool(
        name="sample.slow",
        input_model=ToolInput,
        output_model=ToolOutput,
        handler=slow_tool,
        timeout_seconds=0.01,
    )

    registry.grant_tool(
        agent_name="sample_agent",
        tool_name="sample.slow",
    )

    with pytest.raises(ToolTimeoutError):
        asyncio.run(
            registry.invoke(
                agent_name="sample_agent",
                tool_name="sample.slow",
                payload={"value": 5},
            )
        )


def test_tool_allowlists_are_agent_specific():
    registry = ToolRegistry()

    async def sample_tool(data: ToolInput) -> ToolOutput:
        return ToolOutput(result=data.value)

    registry.register_tool(
        name="sample.read",
        input_model=ToolInput,
        output_model=ToolOutput,
        handler=sample_tool,
    )

    registry.grant_tool(
        agent_name="sample_agent",
        tool_name="sample.read",
    )

    assert "sample.read" in registry.allowed_tools("sample_agent")
    assert "sample.read" not in registry.allowed_tools("another_agent")


def test_tool_registration_rejects_sync_handlers():
    registry = ToolRegistry()

    def sync_tool(data: ToolInput) -> ToolOutput:
        return ToolOutput(result=data.value)

    with pytest.raises(TypeError):
        registry.register_tool(
            name="sample.sync",
            input_model=ToolInput,
            output_model=ToolOutput,
            handler=sync_tool,
        )
