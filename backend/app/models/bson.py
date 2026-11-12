
from decimal import Decimal
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128
from pydantic import BaseModel, BeforeValidator
from typing import Annotated


def validate_decimal(value: Any) -> Decimal:
    """
    Accept Decimal or a decimal string.

    Binary floating-point values are deliberately rejected.
    """

    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(
            "Financial values must not use binary floating-point"
        )

    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except Exception as exc:
            raise ValueError("Invalid decimal value") from exc
    else:
        raise ValueError(
            "Financial values must be Decimal or decimal strings"
        )

    if not result.is_finite():
        raise ValueError("Financial values must be finite")

    return result


Money = Annotated[Decimal, BeforeValidator(validate_decimal)]


def to_bson_value(value: Any) -> Any:
    """Recursively convert Python values into BSON-compatible values."""

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Financial values must be finite")
        return Decimal128(value)

    if isinstance(value, BaseModel):
        return to_bson_value(
            value.model_dump(mode="python", by_alias=True)
        )

    if isinstance(value, dict):
        return {
            key: to_bson_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [to_bson_value(item) for item in value]

    if isinstance(value, tuple):
        return [to_bson_value(item) for item in value]

    return value


def from_bson_value(value: Any) -> Any:
    """Recursively convert BSON Decimal128 values into Python Decimal."""

    if isinstance(value, Decimal128):
        return value.to_decimal()

    if isinstance(value, dict):
        return {
            key: from_bson_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [from_bson_value(item) for item in value]

    return value


def model_to_bson_document(model: BaseModel) -> dict:
    """Serialize a Pydantic document model for MongoDB insertion."""

    return to_bson_value(
        model.model_dump(mode="python", by_alias=True)
    )


def model_from_bson_document(
    model_class: type[BaseModel],
    document: dict,
) -> BaseModel:
    """Validate and deserialize a MongoDB document."""

    return model_class.model_validate(
        from_bson_value(document)
    )
