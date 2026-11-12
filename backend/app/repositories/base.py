
"""Shared tenant-scoped MongoDB repository."""

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import BaseModel
from pymongo.collection import Collection

from app.models.bson import to_bson_value


class BaseRepository:
    """
    Shared repository for tenant-owned MongoDB collections.

    org_id must come from trusted application context, never
    directly from an API request body or query parameter.
    """

    def __init__(self, collection: Collection, org_id: str):
        if not isinstance(org_id, str) or not org_id.strip():
            raise ValueError("A valid organisation ID is required.")

        self.collection = collection
        self.org_id = org_id.strip()

    def _tenant_filter(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Combine caller filters with a mandatory tenant condition."""

        if filters is not None and not isinstance(filters, dict):
            raise TypeError("filters must be a dictionary or None.")

        return {
            "$and": [
                {"org_id": self.org_id},
                filters or {},
            ]
        }

    @staticmethod
    def _document_to_dict(document: BaseModel | dict) -> dict:
        """Convert a Pydantic model or dictionary to BSON values."""

        if isinstance(document, BaseModel):
            data = document.model_dump(
                mode="python",
                by_alias=True,
                exclude={"id"},
            )
        elif isinstance(document, dict):
            data = dict(document)
        else:
            raise TypeError(
                "Document must be a Pydantic model or dictionary."
            )

        return to_bson_value(data)

    def create(self, document: BaseModel | dict) -> dict:
        """Insert one document under this repository's tenant."""

        data = self._document_to_dict(document)
        supplied_org_id = data.get("org_id")

        if supplied_org_id is not None and supplied_org_id != self.org_id:
            raise ValueError(
                "Document organisation does not match context."
            )

        data["org_id"] = self.org_id

        now = datetime.now(timezone.utc)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        data.setdefault("schema_version", 1)

        result = self.collection.insert_one(data)
        data["_id"] = result.inserted_id

        return data

    def get_by_id(self, document_id: str) -> dict | None:
        """Find a document by ID within this organisation."""

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
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        """List documents with mandatory tenant filtering."""

        if not isinstance(skip, int) or isinstance(skip, bool) or skip < 0:
            raise ValueError("skip must be a non-negative integer.")

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
            or limit > 500
        ):
            raise ValueError("limit must be an integer between 1 and 500.")

        cursor = self.collection.find(self._tenant_filter(filters))

        if sort:
            cursor = cursor.sort(sort)

        return list(cursor.skip(skip).limit(limit))

    def update_by_id(
        self,
        document_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update a document without permitting identity reassignment."""

        if not ObjectId.is_valid(document_id):
            return False

        if not isinstance(updates, dict) or not updates:
            raise ValueError("At least one update field is required.")

        forbidden_roots = {"_id", "org_id"}

        for key in updates:
            if not isinstance(key, str) or not key:
                raise ValueError("Update field names must be non-empty strings.")

            if key.startswith("$"):
                raise ValueError(
                    "MongoDB operators are not accepted as update fields."
                )

            root_field = key.split(".", maxsplit=1)[0]

            if root_field in forbidden_roots:
                raise ValueError(
                    "Document identity fields cannot be updated."
                )

        safe_updates = to_bson_value(dict(updates))
        safe_updates["updated_at"] = datetime.now(timezone.utc)

        result = self.collection.update_one(
            {
                "org_id": self.org_id,
                "_id": ObjectId(document_id),
            },
            {"$set": safe_updates},
        )

        return result.matched_count == 1

    def delete_by_id(self, document_id: str) -> bool:
        """Delete a document only within this organisation."""

        if not ObjectId.is_valid(document_id):
            return False

        result = self.collection.delete_one(
            {
                "org_id": self.org_id,
                "_id": ObjectId(document_id),
            }
        )

        return result.deleted_count == 1

    def count(
        self,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count documents belonging to this organisation."""

        return self.collection.count_documents(
            self._tenant_filter(filters)
        )
