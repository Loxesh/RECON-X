
"""Deny-by-default registry for explicitly injected agent capabilities."""

import asyncio
import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from pydantic import BaseModel, ValidationError


InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)

ToolHandler = Callable[[BaseModel], Awaitable[BaseModel | dict]]


class ToolRegistryError(Exception):
    """Base exception for safe tool registry failures."""

    code = "tool_registry_error"


class ToolNotFound(ToolRegistryError):
    code = "tool_not_found"


class ToolPermissionDenied(ToolRegistryError):
    code = "tool_permission_denied"


class ToolValidationError(ToolRegistryError):
    code = "tool_validation_error"


class ToolTimeoutError(ToolRegistryError):
    code = "tool_timeout"


class ToolExecutionError(ToolRegistryError):
    code = "tool_execution_error"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: ToolHandler
    timeout_seconds: float


class ToolRegistry:
    """Registers capabilities and grants them explicitly to named agents.

    No tools are available by default. A tool must be registered and separately
    granted to an agent before that agent can invoke it.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._agent_allowlists: dict[str, frozenset[str]] = {}

    def register_tool(
        self,
        *,
        name: str,
        input_model: type[InputModel],
        output_model: type[OutputModel],
        handler: Callable[
            [InputModel],
            Awaitable[OutputModel | dict],
        ],
        timeout_seconds: float = 10.0,
    ) -> None:
        """Register an async capability without granting it to any agent."""

        if not name or not name.strip():
            raise ValueError("Tool name cannot be blank.")

        if name in self._tools:
            raise ValueError("Tool is already registered.")

        if not inspect.isclass(input_model) or not issubclass(
            input_model, BaseModel
        ):
            raise TypeError("Tool input must be a Pydantic model.")

        if not inspect.isclass(output_model) or not issubclass(
            output_model, BaseModel
        ):
            raise TypeError("Tool output must be a Pydantic model.")

        if not inspect.iscoroutinefunction(handler):
            raise TypeError("Tool handlers must be asynchronous.")

        if timeout_seconds <= 0:
            raise ValueError("Tool timeout must be positive.")

        self._tools[name] = ToolDefinition(
            name=name,
            input_model=input_model,
            output_model=output_model,
            handler=handler,
            timeout_seconds=timeout_seconds,
        )

    def grant_tool(
        self,
        *,
        agent_name: str,
        tool_name: str,
    ) -> None:
        """Explicitly grant one registered capability to one agent."""

        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be blank.")

        if tool_name not in self._tools:
            raise ToolNotFound()

        current = self._agent_allowlists.get(
            agent_name,
            frozenset(),
        )

        self._agent_allowlists[agent_name] = current | {tool_name}

    def revoke_tool(
        self,
        *,
        agent_name: str,
        tool_name: str,
    ) -> None:
        """Revoke a previously granted capability."""

        current = self._agent_allowlists.get(
            agent_name,
            frozenset(),
        )

        self._agent_allowlists[agent_name] = current - {tool_name}

    def allowed_tools(self, agent_name: str) -> frozenset[str]:
        """Return an immutable view of an agent's allowlist."""

        return self._agent_allowlists.get(
            agent_name,
            frozenset(),
        )

    async def invoke(
        self,
        *,
        agent_name: str,
        tool_name: str,
        payload: dict,
    ) -> BaseModel:
        """Validate, authorize and execute one registered capability."""

        allowed = self.allowed_tools(agent_name)

        if tool_name not in allowed:
            raise ToolPermissionDenied()

        definition = self._tools.get(tool_name)

        if definition is None:
            raise ToolNotFound()

        try:
            validated_input = definition.input_model.model_validate(
                payload
            )
        except ValidationError as exc:
            raise ToolValidationError() from exc

        try:
            raw_output = await asyncio.wait_for(
                definition.handler(validated_input),
                timeout=definition.timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise ToolTimeoutError() from exc
        except Exception as exc:
            # Never expose raw handler exceptions, response bodies or secrets.
            raise ToolExecutionError() from exc

        try:
            return definition.output_model.model_validate(raw_output)
        except ValidationError as exc:
            raise ToolValidationError() from exc
