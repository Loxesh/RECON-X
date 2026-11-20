import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.reconciliation.rules import MatchingRuleset, RulesetSnapshot
from app.reconciliation.schemas import (
    MatchEvidence,
    MatchOutcome,
    MatchingResult,
)


def test_default_ruleset_uses_architecture_starting_values():
    rules = MatchingRuleset()

    assert rules.bank_ledger_date_window_days == 2
    assert rules.gateway_ledger_date_window_days == 3
    assert rules.auto_confirm_amount_tolerance == Decimal("0.00")
    assert rules.suggested_amount_tolerance == Decimal("1.00")
    assert rules.fuzzy_threshold == Decimal("0.85")
    assert rules.aggregate_max_group_size == 25


def test_ruleset_priority_is_in_configured_order():
    rules = MatchingRuleset()

    assert rules.rule_priority == (
        "DUPLICATE",
        "EXACT",
        "REFERENCE",
        "TOLERANCE",
        "FUZZY",
        "AGGREGATE",
        "RESIDUAL",
    )


def test_ruleset_rejects_negative_date_window():
    with pytest.raises(ValidationError):
        MatchingRuleset(bank_ledger_date_window_days=-1)


def test_ruleset_rejects_aggregate_group_size_above_25():
    with pytest.raises(ValidationError):
        MatchingRuleset(aggregate_max_group_size=26)


def test_ruleset_rejects_negative_amount_tolerance():
    with pytest.raises(ValidationError):
        MatchingRuleset(auto_confirm_amount_tolerance=Decimal("-0.01"))


def test_ruleset_rejects_float_money_tolerance():
    with pytest.raises(ValidationError):
        MatchingRuleset(suggested_amount_tolerance=0.50)


def test_suggested_tolerance_cannot_be_lower_than_auto_confirm():
    with pytest.raises(ValidationError):
        MatchingRuleset(
            auto_confirm_amount_tolerance=Decimal("2.00"),
            suggested_amount_tolerance=Decimal("1.00"),
        )


def test_ruleset_rejects_invalid_fuzzy_threshold():
    with pytest.raises(ValidationError):
        MatchingRuleset(fuzzy_threshold=Decimal("1.01"))


def test_ruleset_rejects_incomplete_rule_priority():
    with pytest.raises(ValidationError):
        MatchingRuleset(
            rule_priority=("EXACT", "REFERENCE")
        )


def test_ruleset_rejects_duplicate_rule_priority():
    with pytest.raises(ValidationError):
        MatchingRuleset(
            rule_priority=(
                "DUPLICATE",
                "EXACT",
                "REFERENCE",
                "TOLERANCE",
                "FUZZY",
                "AGGREGATE",
                "AGGREGATE",
            )
        )


def test_ruleset_is_immutable():
    rules = MatchingRuleset()

    with pytest.raises(ValidationError):
        rules.version = "2.0.0"


def test_same_ruleset_has_same_fingerprint():
    first = MatchingRuleset()
    second = MatchingRuleset()

    assert first.fingerprint == second.fingerprint


def test_changed_ruleset_has_different_fingerprint():
    first = MatchingRuleset()
    second = MatchingRuleset(version="2.0.0")

    assert first.fingerprint != second.fingerprint


def test_snapshot_preserves_configuration_and_fingerprint():
    rules = MatchingRuleset()
    snapshot = rules.create_snapshot()

    assert snapshot.version == rules.version
    assert snapshot.fingerprint == rules.fingerprint

    configuration = json.loads(snapshot.configuration)
    assert configuration["bank_ledger_date_window_days"] == 2
    assert configuration["aggregate_max_group_size"] == 25


def test_snapshot_rejects_tampered_fingerprint():
    rules = MatchingRuleset()
    snapshot = rules.create_snapshot()

    with pytest.raises(ValidationError):
        RulesetSnapshot(
            version=snapshot.version,
            configuration=snapshot.configuration,
            fingerprint="0" * 64,
        )


def test_matching_result_requires_ruleset_identity():
    result = MatchingResult(
        outcome=MatchOutcome.UNMATCHED,
        ruleset_version="1.0.0",
        ruleset_hash="a" * 64,
    )

    assert result.outcome == MatchOutcome.UNMATCHED
    assert result.ruleset_version == "1.0.0"


def test_matching_result_rejects_invalid_candidate_score():
    with pytest.raises(ValidationError):
        MatchingResult(
            outcome=MatchOutcome.SUGGESTED,
            candidate_score=Decimal("1.2"),
            ruleset_version="1.0.0",
            ruleset_hash="a" * 64,
        )


def test_evidence_schema_preserves_rule_reason_and_fields():
    evidence = MatchEvidence(
        rule_id="EXACT_01",
        rule_priority=1,
        reason="Transaction ID, amount, date and currency agree.",
        compared_fields=("transaction_id", "amount", "currency"),
        observed_values={"currency": "INR"},
    )

    assert evidence.rule_id == "EXACT_01"
    assert "amount" in evidence.compared_fields