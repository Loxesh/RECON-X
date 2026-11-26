
"""Versioned prompt registry for controlled LLM tasks."""

from dataclasses import dataclass
from string import Formatter


class PromptRegistryError(ValueError):
    """Raised for unknown prompts or invalid prompt variables."""


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Immutable versioned prompt definition."""

    name: str
    version: str
    template: str
    required_variables: tuple[str, ...]


class PromptRegistry:
    """Stores and renders explicitly registered prompt versions."""

    def __init__(self) -> None:
        self._prompts: dict[tuple[str, str], PromptTemplate] = {}

    def register(self, prompt: PromptTemplate) -> None:
        key = (prompt.name, prompt.version)

        if key in self._prompts:
            raise PromptRegistryError(
                f"Prompt '{prompt.name}' version '{prompt.version}' "
                "is already registered."
            )

        if not prompt.name.strip() or not prompt.version.strip():
            raise PromptRegistryError("Prompt name and version are required.")

        if not prompt.template.strip():
            raise PromptRegistryError("Prompt template cannot be empty.")

        if len(prompt.template) > 20_000:
            raise PromptRegistryError("Prompt template exceeds the size limit.")

        actual_variables = {
            field_name
            for _, field_name, _, _ in Formatter().parse(prompt.template)
            if field_name is not None
        }

        expected_variables = set(prompt.required_variables)

        if actual_variables != expected_variables:
            raise PromptRegistryError(
                "Prompt placeholders must exactly match required_variables."
            )

        self._prompts[key] = prompt

    def get(self, name: str, version: str) -> PromptTemplate:
        try:
            return self._prompts[(name, version)]
        except KeyError as exc:
            raise PromptRegistryError(
                f"Prompt '{name}' version '{version}' is not registered."
            ) from exc

    def render(
        self,
        name: str,
        version: str,
        variables: dict[str, str],
    ) -> str:
        prompt = self.get(name, version)

        if not isinstance(variables, dict):
            raise PromptRegistryError("Prompt variables must be a dictionary.")

        supplied_variables = set(variables)
        required_variables = set(prompt.required_variables)

        missing = required_variables - supplied_variables
        unexpected = supplied_variables - required_variables

        if missing:
            raise PromptRegistryError(
                f"Missing prompt variables: {', '.join(sorted(missing))}."
            )

        if unexpected:
            raise PromptRegistryError(
                f"Unexpected prompt variables: {', '.join(sorted(unexpected))}."
            )

        if any(not isinstance(value, str) for value in variables.values()):
            raise PromptRegistryError("All prompt variable values must be strings.")

        try:
            rendered = prompt.template.format_map(variables)
        except (KeyError, ValueError, IndexError) as exc:
            raise PromptRegistryError("Unable to render the registered prompt.") from exc

        if len(rendered) > 30_000:
            raise PromptRegistryError("Rendered prompt exceeds the size limit.")

        return rendered


def create_default_prompt_registry() -> PromptRegistry:
    """Create the initial immutable-by-convention application prompt set."""

    registry = PromptRegistry()

    registry.register(
        PromptTemplate(
            name="reconciliation_explanation",
            version="1.0.0",
            required_variables=("task_context", "evidence_json"),
            template=(
                "You are generating an evidence-backed reconciliation explanation.\n"
                "Use only the supplied evidence records and task context.\n"
                "Do not invent record IDs, transactions, amounts, events or facts.\n"
                "Every claim must include one or more evidence_record_ids from the "
                "supplied evidence.\n"
                "If the evidence does not support a conclusion, state that the "
                "available evidence is insufficient.\n"
                "Return only a JSON object matching the required output schema.\n\n"
                "Task context:\n{task_context}\n\n"
                "Supplied evidence records:\n{evidence_json}\n"
            ),
        )
    )

    return registry


prompt_registry = create_default_prompt_registry()
