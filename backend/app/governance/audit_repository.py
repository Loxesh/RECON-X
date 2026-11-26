"""Transactional, append-only, tenant-scoped audit event repository."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.bson import to_bson_value


class AuditChainError(RuntimeError):
    """Raised when an audit chain operation cannot be completed."""


class AuditChainVerificationError(AuditChainError):
    """Raised when an audit chain contains invalid or altered data."""


class AuditRepository:
    """Append-only audit repository with atomic sequence allocation."""

    MAX_APPEND_ATTEMPTS = 5

    HASH_FIELDS = (
        "org_id",
        "seq",
        "ts",
        "event_type",
        "actor",
        "resource",
        "action",
        "outcome",
        "details",
        "correlation_id",
        "prev_hash",
    )

    def __init__(self, database: Database, org_id: str):
        if not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("A valid organisation ID is required.")

        self.database = database
        self.org_id = org_id.strip()
        self.collection: Collection = database["audit_events"]

    @staticmethod
    def _bson_datetime(value: datetime) -> datetime:
        """Normalize a datetime to BSON's millisecond precision."""

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        value = value.astimezone(timezone.utc)

        return value.replace(
            microsecond=(value.microsecond // 1000) * 1000
        )

    @staticmethod
    def _normalise(value: Any) -> Any:
        """Convert supported values into deterministic JSON values."""

        if isinstance(value, Enum):
            return AuditRepository._normalise(value.value)

        if isinstance(value, datetime):
            value = AuditRepository._bson_datetime(value)
            return value.isoformat(timespec="milliseconds")

        if isinstance(value, ObjectId):
            return str(value)

        if isinstance(value, Decimal128):
            return str(value.to_decimal())

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, dict):
            return {
                str(key): AuditRepository._normalise(item)
                for key, item in sorted(
                    value.items(),
                    key=lambda pair: str(pair[0]),
                )
            }

        if isinstance(value, (list, tuple)):
            return [
                AuditRepository._normalise(item)
                for item in value
            ]

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        raise TypeError(
            f"Unsupported audit payload value: {type(value).__name__}"
        )

    @classmethod
    def canonical_payload(cls, event: dict[str, Any]) -> bytes:
        """Build deterministic bytes from authoritative event fields."""

        payload = {
            field: event.get(field)
            for field in cls.HASH_FIELDS
        }

        normalised = cls._normalise(payload)

        return json.dumps(
            normalised,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")

    @classmethod
    def calculate_hash(cls, event: dict[str, Any]) -> str:
        """Calculate SHA-256 over the canonical event payload."""

        return hashlib.sha256(
            cls.canonical_payload(event)
        ).hexdigest()

    def _validate_input(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise TypeError("Audit event must be a dictionary.")

        data = dict(event)

        supplied_org_id = data.pop("org_id", self.org_id)

        if supplied_org_id != self.org_id:
            raise ValueError(
                "Audit event organisation does not match context."
            )

        if any(
            field in data
            for field in ("seq", "hash", "prev_hash")
        ):
            raise ValueError(
                "Sequence and hash fields are allocated by the repository."
            )

        required_fields = (
            "ts",
            "event_type",
            "actor",
            "resource",
            "action",
            "outcome",
            "correlation_id",
        )

        missing = [
            field for field in required_fields
            if field not in data
        ]

        if missing:
            raise ValueError(
                f"Missing required audit fields: {', '.join(missing)}"
            )

        if (
            not isinstance(data["event_type"], str)
            or not data["event_type"].strip()
        ):
            raise ValueError("event_type must be a non-empty string.")

        if (
            not isinstance(data["action"], str)
            or not data["action"].strip()
        ):
            raise ValueError("action must be a non-empty string.")

        if (
            not isinstance(data["correlation_id"], str)
            or not data["correlation_id"].strip()
        ):
            raise ValueError(
                "correlation_id must be a non-empty string."
            )

        if not isinstance(data["ts"], datetime):
            raise TypeError("Audit timestamp must be a datetime.")

        data["ts"] = self._bson_datetime(data["ts"])

        if not isinstance(data["actor"], dict):
            raise TypeError("actor must be a dictionary.")

        if not isinstance(data["resource"], dict):
            raise TypeError("resource must be a dictionary.")

        if not isinstance(data.get("details", {}), dict):
            raise TypeError("details must be a dictionary.")

        data["details"] = data.get("details", {})

        return data

    def _append_in_transaction(
        self,
        data: dict[str, Any],
        session: Any,
    ) -> dict[str, Any]:
        """Append an event using a transaction owned by the caller."""

        latest = self.collection.find_one(
            {"org_id": self.org_id},
            sort=[("seq", DESCENDING)],
            session=session,
        )

        sequence = (
            latest["seq"] + 1
            if latest is not None
            else 1
        )

        previous_hash = (
            latest["hash"]
            if latest is not None
            else None
        )

        created_at = self._bson_datetime(
            datetime.now(timezone.utc)
        )

        document = {
            **data,
            "org_id": self.org_id,
            "seq": sequence,
            "prev_hash": previous_hash,
            "created_at": created_at,
            "updated_at": created_at,
            "schema_version": 1,
        }

        document["hash"] = self.calculate_hash(document)

        persisted = to_bson_value(document)

        result = self.collection.insert_one(
            persisted,
            session=session,
        )

        persisted["_id"] = result.inserted_id

        return persisted

    def append(
        self,
        event: dict[str, Any],
        *,
        session: Any | None = None,
    ) -> dict[str, Any]:
        """
        Append one audit event.

        When session is supplied, the caller owns the transaction.
        When omitted, this method creates and owns its transaction.
        """

        data = self._validate_input(event)

        if session is not None:
            try:
                return self._append_in_transaction(data, session)
            except PyMongoError as exc:
                raise AuditChainError(
                    "MongoDB audit append failed inside the supplied transaction."
                ) from exc

        client = self.database.client

        for attempt in range(self.MAX_APPEND_ATTEMPTS):
            try:
                with client.start_session() as active_session:
                    return active_session.with_transaction(
                        lambda transaction_session:
                            self._append_in_transaction(
                                data,
                                transaction_session,
                            )
                    )

            except DuplicateKeyError as exc:
                if attempt == self.MAX_APPEND_ATTEMPTS - 1:
                    raise AuditChainError(
                        "Could not allocate a unique audit sequence after retries."
                    ) from exc

                time.sleep(0.02 * (attempt + 1))

            except PyMongoError as exc:
                raise AuditChainError(
                    "MongoDB audit transaction failed."
                ) from exc

        raise AuditChainError("Audit append failed.")

    def list_events(self) -> list[dict[str, Any]]:
        """Return this tenant's audit events in sequence order."""

        return list(
            self.collection.find(
                {"org_id": self.org_id}
            ).sort("seq", ASCENDING)
        )

    def verify_chain(self) -> dict[str, Any]:
        """Verify sequence continuity, previous hashes and event hashes."""

        events = self.list_events()

        expected_sequence = 1
        previous_hash = None

        for event in events:
            if event.get("seq") != expected_sequence:
                return {
                    "valid": False,
                    "org_id": self.org_id,
                    "verified_events": expected_sequence - 1,
                    "failed_sequence": event.get("seq"),
                    "reason": "Sequence gap or duplicate position detected.",
                }

            if event.get("prev_hash") != previous_hash:
                return {
                    "valid": False,
                    "org_id": self.org_id,
                    "verified_events": expected_sequence - 1,
                    "failed_sequence": expected_sequence,
                    "reason": "Previous hash does not match the chain.",
                }

            expected_hash = self.calculate_hash(event)

            if event.get("hash") != expected_hash:
                return {
                    "valid": False,
                    "org_id": self.org_id,
                    "verified_events": expected_sequence - 1,
                    "failed_sequence": expected_sequence,
                    "reason": "Audit event payload hash mismatch.",
                }

            previous_hash = event["hash"]
            expected_sequence += 1

        return {
            "valid": True,
            "org_id": self.org_id,
            "verified_events": len(events),
            "last_sequence": len(events),
            "last_hash": previous_hash,
            "reason": "Audit chain verified successfully.",
        }