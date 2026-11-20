import hashlib
import json
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MatchingRuleset(BaseModel):
    """
    Immutable, versioned matching configuration.

    Defaults follow the proposed starting values in the approved
    RECON X architecture. Organisations can supply their own values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(default="1.0.0", min_length=1)

    # Ordered matching cascade.
    rule_priority: tuple[str, ...] = (
        "DUPLICATE",
        "EXACT",
        "REFERENCE",
        "TOLERANCE",
        "FUZZY",
        "AGGREGATE",
        "RESIDUAL",
    )

    bank_ledger_date_window_days: int = Field(default=2, ge=0)
    gateway_ledger_date_window_days: int = Field(default=3, ge=0)

    auto_confirm_amount_tolerance: Decimal = Decimal("0.00")
    suggested_amount_tolerance: Decimal = Decimal("1.00")

    fuzzy_threshold: Decimal = Decimal("0.85")
    aggregate_max_group_size: int = Field(default=25, ge=1, le=25)

    # Optional gateway-specific fee tolerances.
    gateway_fee_tolerances: tuple[tuple[str, Decimal], ...] = ()

    @field_validator(
        "auto_confirm_amount_tolerance",
        "suggested_amount_tolerance",
        mode="before",
    )
    @classmethod
    def validate_decimal_tolerances(cls, value: Any) -> Decimal:
        if isinstance(value, (float, bool)):
            raise ValueError("Money tolerances must not use float or boolean.")

        try:
            amount = Decimal(str(value))
        except Exception as exc:
            raise ValueError("Tolerance must be a valid Decimal.") from exc

        if not amount.is_finite() or amount < 0:
            raise ValueError("Tolerance must be finite and non-negative.")

        return amount

    @field_validator("fuzzy_threshold", mode="before")
    @classmethod
    def validate_fuzzy_threshold(cls, value: Any) -> Decimal:
        if isinstance(value, (float, bool)):
            raise ValueError("Fuzzy threshold must not use float or boolean.")

        try:
            threshold = Decimal(str(value))
        except Exception as exc:
            raise ValueError("Fuzzy threshold must be a valid Decimal.") from exc

        if (
            not threshold.is_finite()
            or threshold < Decimal("0")
            or threshold > Decimal("1")
        ):
            raise ValueError("Fuzzy threshold must be between 0 and 1.")

        return threshold

    @model_validator(mode="after")
    def validate_ruleset(self):
        if self.suggested_amount_tolerance < self.auto_confirm_amount_tolerance:
            raise ValueError(
                "Suggested tolerance cannot be lower than auto-confirm tolerance."
            )

        required = {
            "DUPLICATE",
            "EXACT",
            "REFERENCE",
            "TOLERANCE",
            "FUZZY",
            "AGGREGATE",
            "RESIDUAL",
        }

        if len(self.rule_priority) != len(set(self.rule_priority)):
            raise ValueError("Rule priority cannot contain duplicate entries.")

        if set(self.rule_priority) != required:
            raise ValueError(
                "Rule priority must contain every supported pass exactly once."
            )

        gateway_names = [name for name, _ in self.gateway_fee_tolerances]
        if len(gateway_names) != len(set(gateway_names)):
            raise ValueError("Gateway fee tolerance names must be unique.")

        for gateway, tolerance in self.gateway_fee_tolerances:
            if not gateway.strip():
                raise ValueError("Gateway name cannot be empty.")
            if not tolerance.is_finite() or tolerance < 0:
                raise ValueError(
                    "Gateway fee tolerances must be finite and non-negative."
                )

        return self

    def canonical_json(self) -> str:
        """Return deterministic JSON for this exact ruleset."""

        payload = self.model_dump(mode="json")
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    @property
    def fingerprint(self) -> str:
        """SHA-256 fingerprint identifying this ruleset configuration."""

        return hashlib.sha256(
            self.canonical_json().encode("utf-8")
        ).hexdigest()

    def create_snapshot(self) -> "RulesetSnapshot":
        """Create a self-contained immutable snapshot for a reconciliation run."""

        return RulesetSnapshot(
            version=self.version,
            configuration=self.canonical_json(),
            fingerprint=self.fingerprint,
        )


class RulesetSnapshot(BaseModel):
    """Persistable snapshot identifying the exact rules used by a run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(min_length=1)
    configuration: str = Field(min_length=2)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def verify_fingerprint(self):
        expected = hashlib.sha256(
            self.configuration.encode("utf-8")
        ).hexdigest()

        if self.fingerprint != expected:
            raise ValueError("Ruleset snapshot fingerprint does not match.")

        try:
            json.loads(self.configuration)
        except json.JSONDecodeError as exc:
            raise ValueError("Ruleset snapshot configuration is invalid JSON.") from exc

        return self