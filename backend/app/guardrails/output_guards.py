
"""Strict validation for structured LLM explanations and evidence references."""

import json
from collections.abc import Collection
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


MAX_OUTPUT_CHARACTERS = 20_000


class OutputValidationError(ValueError):
    """Raised when generated LLM output is malformed or unsupported."""


class EvidenceClaim(BaseModel):
    """A single explanation claim backed by supplied evidence records."""

    model_config = ConfigDict(extra="forbid", strict=True)

    claim: str = Field(min_length=1, max_length=2_000)
    evidence_record_ids: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> "EvidenceClaim":
        if len(self.evidence_record_ids) != len(set(self.evidence_record_ids)):
            raise ValueError("Duplicate evidence record IDs are not allowed.")

        if any(not record_id.strip() for record_id in self.evidence_record_ids):
            raise ValueError("Evidence record IDs cannot be blank.")

        return self


class LLMExplanationOutput(BaseModel):
    """Strict structured response accepted from the LLM gateway."""

    model_config = ConfigDict(extra="forbid", strict=True)

    explanation: str = Field(min_length=1, max_length=8_000)
    claims: list[EvidenceClaim] = Field(min_length=1, max_length=20)
    cited_record_ids: list[str] = Field(min_length=1, max_length=100)
    recommended_actions: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_citation_consistency(self) -> "LLMExplanationOutput":
        if any(not action.strip() for action in self.recommended_actions):
            raise ValueError("Recommended actions cannot be blank.")

        if any(len(action) > 500 for action in self.recommended_actions):
            raise ValueError("Recommended actions cannot exceed 500 characters.")

        if any(not record_id.strip() for record_id in self.cited_record_ids):
            raise ValueError("Cited record IDs cannot be blank.")

        if len(self.cited_record_ids) != len(set(self.cited_record_ids)):
            raise ValueError("Duplicate cited record IDs are not allowed.")

        claim_evidence_ids = {
            record_id
            for claim in self.claims
            for record_id in claim.evidence_record_ids
        }

        cited_ids = set(self.cited_record_ids)

        if claim_evidence_ids != cited_ids:
            raise ValueError(
                "Top-level citations must exactly match the evidence IDs "
                "referenced by the claims."
            )

        return self


def validate_explanation_output(
    raw_output: str,
    evidence_record_ids: Collection[str],
    *,
    max_output_characters: int = MAX_OUTPUT_CHARACTERS,
) -> LLMExplanationOutput:
    """
    Parse and validate generated JSON against supplied evidence IDs.

    This function verifies schema correctness and evidence-reference integrity.
    It does not independently establish the factual truth of a natural-language
    claim; downstream review must retain the referenced evidence.
    """

    if not isinstance(raw_output, str):
        raise OutputValidationError("LLM output must be a JSON string.")

    if not isinstance(max_output_characters, int) or max_output_characters < 1:
        raise ValueError("Maximum output length must be a positive integer.")

    if len(raw_output) > max_output_characters:
        raise OutputValidationError("LLM output exceeds the permitted length.")

    if not raw_output.strip():
        raise OutputValidationError("LLM output cannot be empty.")

    allowed_ids = set(evidence_record_ids)

    if not allowed_ids:
        raise OutputValidationError("No evidence records were supplied.")

    if any(not isinstance(item, str) or not item.strip() for item in allowed_ids):
        raise OutputValidationError("Supplied evidence contains an invalid record ID.")

    try:
        parsed: Any = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise OutputValidationError("LLM output is not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise OutputValidationError("LLM output must be a JSON object.")

    try:
        result = LLMExplanationOutput.model_validate(parsed)
    except ValidationError as exc:
        raise OutputValidationError(
            "LLM output does not match the required explanation schema."
        ) from exc

    referenced_ids = set(result.cited_record_ids)

    for claim in result.claims:
        referenced_ids.update(claim.evidence_record_ids)

    unknown_ids = referenced_ids - allowed_ids

    if unknown_ids:
        raise OutputValidationError(
            "LLM output references evidence records that were not supplied."
        )

    return result
