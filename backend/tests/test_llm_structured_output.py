
"""Tests for Chapter 33 prompt registry and structured output guardrails."""

import json

import pytest

from app.guardrails.output_guards import (
    LLMExplanationOutput,
    OutputValidationError,
    validate_explanation_output,
)
from app.llm.prompt_registry import (
    PromptRegistry,
    PromptRegistryError,
    PromptTemplate,
    create_default_prompt_registry,
)


VALID_OUTPUT = {
    "explanation": "The payment amount differs from the bank record.",
    "claims": [
        {
            "claim": "The payment amount differs from the bank record.",
            "evidence_record_ids": ["TXN001", "BANK001"],
        }
    ],
    "cited_record_ids": ["TXN001", "BANK001"],
    "recommended_actions": ["Review the payment discrepancy."],
}

VALID_EVIDENCE = {"TXN001", "BANK001"}


def test_valid_structured_output_is_accepted():
    result = validate_explanation_output(
        json.dumps(VALID_OUTPUT),
        VALID_EVIDENCE,
    )

    assert isinstance(result, LLMExplanationOutput)
    assert result.cited_record_ids == ["TXN001", "BANK001"]


def test_malformed_json_is_rejected():
    with pytest.raises(OutputValidationError, match="valid JSON"):
        validate_explanation_output(
            '{"explanation": ',
            VALID_EVIDENCE,
        )


def test_missing_required_field_is_rejected():
    payload = VALID_OUTPUT.copy()
    payload.pop("claims")

    with pytest.raises(OutputValidationError, match="required explanation schema"):
        validate_explanation_output(json.dumps(payload), VALID_EVIDENCE)


def test_extra_field_is_rejected():
    payload = {**VALID_OUTPUT, "unsupported_metadata": "not allowed"}

    with pytest.raises(OutputValidationError, match="required explanation schema"):
        validate_explanation_output(json.dumps(payload), VALID_EVIDENCE)


def test_invented_record_id_is_rejected():
    payload = json.loads(json.dumps(VALID_OUTPUT))
    payload["claims"][0]["evidence_record_ids"].append("INVENTED999")
    payload["cited_record_ids"].append("INVENTED999")

    with pytest.raises(OutputValidationError, match="not supplied"):
        validate_explanation_output(json.dumps(payload), VALID_EVIDENCE)


def test_claim_without_evidence_is_rejected():
    payload = json.loads(json.dumps(VALID_OUTPUT))
    payload["claims"][0]["evidence_record_ids"] = []
    payload["cited_record_ids"] = []

    with pytest.raises(OutputValidationError, match="required explanation schema"):
        validate_explanation_output(json.dumps(payload), VALID_EVIDENCE)


def test_citations_must_match_claim_evidence():
    payload = json.loads(json.dumps(VALID_OUTPUT))
    payload["cited_record_ids"] = ["TXN001"]

    with pytest.raises(OutputValidationError, match="required explanation schema"):
        validate_explanation_output(json.dumps(payload), VALID_EVIDENCE)


def test_overlong_output_is_rejected():
    with pytest.raises(OutputValidationError, match="exceeds the permitted length"):
        validate_explanation_output(
            json.dumps(VALID_OUTPUT),
            VALID_EVIDENCE,
            max_output_characters=10,
        )


def test_non_object_json_is_rejected():
    with pytest.raises(OutputValidationError, match="JSON object"):
        validate_explanation_output(
            json.dumps(["not", "an", "object"]),
            VALID_EVIDENCE,
        )


def test_empty_evidence_is_rejected():
    with pytest.raises(OutputValidationError, match="No evidence records"):
        validate_explanation_output(json.dumps(VALID_OUTPUT), set())


def test_prompt_registry_renders_registered_version():
    registry = create_default_prompt_registry()

    rendered = registry.render(
        "reconciliation_explanation",
        "1.0.0",
        {
            "task_context": "Investigate payment discrepancy.",
            "evidence_json": '[{"record_id": "TXN001"}]',
        },
    )

    assert "Investigate payment discrepancy." in rendered
    assert "TXN001" in rendered
    assert "Do not invent record IDs" in rendered


def test_prompt_registry_rejects_unknown_version():
    registry = create_default_prompt_registry()

    with pytest.raises(PromptRegistryError, match="not registered"):
        registry.get("reconciliation_explanation", "9.9.9")


def test_prompt_registry_rejects_missing_variables():
    registry = create_default_prompt_registry()

    with pytest.raises(PromptRegistryError, match="Missing prompt variables"):
        registry.render(
            "reconciliation_explanation",
            "1.0.0",
            {"task_context": "Investigate."},
        )


def test_prompt_registry_rejects_unexpected_variables():
    registry = create_default_prompt_registry()

    with pytest.raises(PromptRegistryError, match="Unexpected prompt variables"):
        registry.render(
            "reconciliation_explanation",
            "1.0.0",
            {
                "task_context": "Investigate.",
                "evidence_json": "[]",
                "extra": "not allowed",
            },
        )


def test_prompt_registry_rejects_duplicate_versions():
    registry = PromptRegistry()
    prompt = PromptTemplate(
        name="test_prompt",
        version="1.0.0",
        template="Explain {context}.",
        required_variables=("context",),
    )

    registry.register(prompt)

    with pytest.raises(PromptRegistryError, match="already registered"):
        registry.register(prompt)
