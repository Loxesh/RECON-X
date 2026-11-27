
"""Shared base class for controlled RECON X agent execution."""

import asyncio
from abc import ABC, abstractmethod
from enum import StrEnum
from time import perf_counter
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agents.tool_registry import ToolRegistry


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentStatus(StrEnum):
    SUCCESS = "SUCCESS"
    INVALID_INPUT = "INVALID_INPUT"
    TIMED_OUT = "TIMED_OUT"
    FAILED = "FAILED"


class AgentContext(BaseModel):
    """Trusted execution metadata supplied by the application.

    Callers must derive tenant and workflow identifiers from trusted
    authenticated application context, not untrusted agent input.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_id: str = Field(min_length=1, max_length=128)
    job_id: str = Field(min_length=1, max_length=128)
    workflow_run_id: str = Field(min_length=1, max_length=128)
    correlation_id: str = Field(min_length=1, max_length=128)


class AgentResult(BaseModel, Generic[OutputT]):
    """Typed result returned from every agent execution."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str
    status: AgentStatus
    output: OutputT | None = None
    duration_ms: int = Field(default=0, ge=0)
    error_code: str | None = None


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Common execution lifecycle for all RECON X agents.

    Subclasses provide validated input/output schemas and implement execute().
    Tool access is available only through the injected ToolRegistry.
    """

    agent_name: str
    input_model: type[InputT]
    output_model: type[OutputT]

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not self.agent_name or not self.agent_name.strip():
            raise ValueError("Agent name must be defined.")

        if timeout_seconds <= 0:
            raise ValueError("Agent timeout must be positive.")

        self._tool_registry = tool_registry
        self._timeout_seconds = timeout_seconds

    @abstractmethod
    async def execute(
        self,
        input_data: InputT,
        context: AgentContext,
    ) -> OutputT:
        """Execute the agent's business logic."""

    async def invoke_tool(
        self,
        *,
        tool_name: str,
        payload: dict,
    ) -> BaseModel:
        """Invoke a capability through the agent-specific allowlist."""

        return await self._tool_registry.invoke(
            agent_name=self.agent_name,
            tool_name=tool_name,
            payload=payload,
        )

    async def run(
        self,
        *,
        payload: dict,
        context: AgentContext,
    ) -> AgentResult[OutputT]:
        """Validate and execute the agent within its configured timeout."""

        started = perf_counter()

        try:
            validated_input = self.input_model.model_validate(payload)
        except ValidationError:
            return self._result(
                status=AgentStatus.INVALID_INPUT,
                started=started,
                error_code="invalid_agent_input",
            )

        try:
            raw_output = await asyncio.wait_for(
                self.execute(validated_input, context),
                timeout=self._timeout_seconds,
            )

            validated_output = self.output_model.model_validate(
                raw_output
            )

            return self._result(
                status=AgentStatus.SUCCESS,
                started=started,
                output=validated_output,
            )

        except asyncio.TimeoutError:
            return self._result(
                status=AgentStatus.TIMED_OUT,
                started=started,
                error_code="agent_timeout",
            )

        except Exception:
            # Keep internal exception messages and sensitive data private.
            return self._result(
                status=AgentStatus.FAILED,
                started=started,
                error_code="agent_execution_failed",
            )

    def _result(
        self,
        *,
        status: AgentStatus,
        started: float,
        output: OutputT | None = None,
        error_code: str | None = None,
    ) -> AgentResult[OutputT]:
        duration_ms = max(
            0,
            int((perf_counter() - started) * 1000),
        )

        return AgentResult[OutputT](
            agent_name=self.agent_name,
            status=status,
            output=output,
            duration_ms=duration_ms,
            error_code=error_code,
        )
