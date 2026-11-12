
"""Repository for organisation documents."""

from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.database import Database

from app.models.bson import to_bson_value


class OrganizationRepository:
    """Repository for organisations, which are not tenant-owned documents."""

    def __init__(self, database: Database):
        self.collection: Collection = database["organizations"]

    @staticmethod
    def _to_dict(document: BaseModel | dict) -> dict:
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
        data = self._to_dict(document)

        now = datetime.now(timezone.utc)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        data.setdefault("schema_version", 1)

        result = self.collection.insert_one(data)
        data["_id"] = result.inserted_id

        return data

    def get_by_id(self, organization_id: str) -> dict | None:
        if not ObjectId.is_valid(organization_id):
            return None

        return self.collection.find_one(
            {"_id": ObjectId(organization_id)}
        )

    def get_by_slug(self, slug: str) -> dict | None:
        if not isinstance(slug, str) or not slug.strip():
            return None

        return self.collection.find_one({"slug": slug.strip()})

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        if not isinstance(skip, int) or isinstance(skip, bool) or skip < 0:
            raise ValueError("skip must be a non-negative integer.")

        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
            or limit > 500
        ):
            raise ValueError("limit must be an integer between 1 and 500.")

        cursor = self.collection.find({})
        return list(cursor.skip(skip).limit(limit))

    def update_by_id(
        self,
        organization_id: str,
        updates: dict,
    ) -> bool:
        if not ObjectId.is_valid(organization_id):
            return False

        if not isinstance(updates, dict) or not updates:
            raise ValueError("At least one update field is required.")

        forbidden_fields = {"_id", "created_at", "schema_version"}

        for key in updates:
            if not isinstance(key, str) or not key:
                raise ValueError("Update field names must be non-empty strings.")

            if key.startswith("$"):
                raise ValueError("MongoDB operators are not accepted.")

            if key.split(".", maxsplit=1)[0] in forbidden_fields:
                raise ValueError("Protected organisation fields cannot be updated.")

        safe_updates = to_bson_value(dict(updates))
        safe_updates["updated_at"] = datetime.now(timezone.utc)

        result = self.collection.update_one(
            {"_id": ObjectId(organization_id)},
            {"$set": safe_updates},
        )

        return result.matched_count == 1

    def count(self) -> int:
        return self.collection.count_documents({})
