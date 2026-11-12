
"""Append-only, tenant-scoped audit event repository."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.database import Database

from app.models.bson import to_bson_value


class AuditEventRepository:
    """
    Append-only repository for audit events.

    Events cannot be updated or deleted through this repository.
    The tenant ID must come from trusted application context.
    """

    def __init__(self, database: Database, org_id: str):
        if not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("A valid organisation ID is required.")

        self.collection: Collection = database["audit_events"]
        self.org_id = org_id.strip()

    @staticmethod
    def _to_dict(event: BaseModel | dict) -> dict:
        if isinstance(event, BaseModel):
            data = event.model_dump(
                mode="python",
                by_alias=True,
                exclude={"id"},
            )
        elif isinstance(event, dict):
            data = dict(event)
        else:
            raise TypeError(
                "Audit event must be a Pydantic model or dictionary."
            )

        return to_bson_value(data)

    def append(self, event: BaseModel | dict) -> dict:
        """Append one immutable audit event for this organisation."""

        data = self._to_dict(event)

        supplied_org_id = data.get("org_id")

        if supplied_org_id is not None and supplied_org_id != self.org_id:
            raise ValueError(
                "Audit event organisation does not match context."
            )

        data["org_id"] = self.org_id
        data.setdefault("created_at", datetime.now(timezone.utc))
        data.setdefault("updated_at", data["created_at"])
        data.setdefault("schema_version", 1)

        result = self.collection.insert_one(data)
        data["_id"] = result.inserted_id

        return data

    def get_by_id(self, document_id: str) -> dict | None:
        """Retrieve an audit event within this organisation."""

        from bson import ObjectId

        if not ObjectId.is_valid(document_id):
            return None

        return self.collection.find_one(
            {
                "org_id": self.org_id,
                "_id": ObjectId(document_id),
            }
        )

    def list(
        self,
        filters: dict[str, Any] | None = None,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """List audit events without allowing tenant filter overrides."""

        if filters is not None and not isinstance(filters, dict):
            raise TypeError("filters must be a dictionary or None.")

        if not isinstance(skip, int) or isinstance(skip, bool) or skip < 0:
            raise ValueError("skip must be a non-negative integer.")

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
            or limit > 500
        ):
            raise ValueError("limit must be an integer between 1 and 500.")

        query = {
            "$and": [
                {"org_id": self.org_id},
                filters or {},
            ]
        }

        cursor = self.collection.find(query).sort(
            [("seq", 1)]
        )

        return list(cursor.skip(skip).limit(limit))

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count audit events belonging to this organisation."""

        if filters is not None and not isinstance(filters, dict):
            raise TypeError("filters must be a dictionary or None.")

        query = {
            "$and": [
                {"org_id": self.org_id},
                filters or {},
            ]
        }

        return self.collection.count_documents(query)
