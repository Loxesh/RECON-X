"""Deterministic detection of common prompt-injection indicators."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InjectionFinding:
    """A detected prompt-injection indicator."""

    rule: str
    description: str


@dataclass(frozen=True, slots=True)
class InjectionInspection:
    """Inspection result for untrusted text."""

    findings: tuple[InjectionFinding, ...]

    @property
    def is_suspicious(self) -> bool:
        return bool(self.findings)


class PromptInjectionError(ValueError):
    """Raised when a caller explicitly rejects suspicious input."""


_INJECTION_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "ignore_previous_instructions",
        "Attempts to override or ignore previous instructions.",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b"
            r".{0,80}\b(previous|prior|above|all|system)\b"
            r".{0,40}\b(instructions?|rules?|prompts?|polic(?:y|ies))\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "system_prompt_disclosure",
        "Attempts to reveal hidden system or developer instructions.",
        re.compile(
            r"\b(reveal|show|print|disclose|repeat|expose)\b"
            r".{0,80}\b(system|developer)\b"
            r".{0,40}\b(prompt|instructions?|message)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "role_impersonation",
        "Contains an apparent attempt to impersonate a privileged role.",
        re.compile(
            r"(?im)^\s*(system|developer)\s*:\s*",
        ),
    ),
    (
        "tool_execution_request",
        "Attempts to make the model execute a tool or external action.",
        re.compile(
            r"\b(call|invoke|execute|run|trigger)\b"
            r".{0,60}\b(tool|function|api|command|shell|browser)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "instruction_hierarchy_override",
        "Attempts to establish a new instruction hierarchy.",
        re.compile(
            r"\b(new|updated|replacement|highest.priority)\b"
            r".{0,50}\b(system|developer)\b"
            r".{0,40}\b(instructions?|policy|rules?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "secret_exfiltration",
        "Requests disclosure of credentials or secret configuration.",
        re.compile(
            r"\b(reveal|print|send|exfiltrate|output|show)\b"
            r".{0,60}\b(api keys?|passwords?|secrets?|credentials?|tokens?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


def inspect_prompt_injection(text: str) -> InjectionInspection:
    """Identify common injection indicators without executing or modifying text."""

    if not isinstance(text, str):
        raise TypeError("Prompt-injection inspection requires a string.")

    findings = tuple(
        InjectionFinding(rule=rule, description=description)
        for rule, description, pattern in _INJECTION_PATTERNS
        if pattern.search(text)
    )

    return InjectionInspection(findings=findings)


def contains_prompt_injection(text: str) -> bool:
    """Return whether known prompt-injection indicators were detected."""

    return inspect_prompt_injection(text).is_suspicious


def reject_detected_prompt_injection(text: str) -> None:
    """Explicitly reject text when a caller requires a strict detection policy."""

    inspection = inspect_prompt_injection(text)

    if inspection.is_suspicious:
        detected_rules = ", ".join(
            finding.rule for finding in inspection.findings
        )
        raise PromptInjectionError(
            f"Suspicious prompt-injection indicators detected: {detected_rules}."
        )
