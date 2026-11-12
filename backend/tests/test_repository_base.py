
from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from app.repositories.base import BaseRepository


@pytest.fixture
def collection():
    return MagicMock()


@pytest.fixture
def repository(collection):
    return BaseRepository(collection, "ORG001")


def test_repository_requires_organisation_id(collection):
    with pytest.raises(ValueError):
        BaseRepository(collection, "")


def test_create_injects_tenant_id(repository, collection):
    inserted_id = ObjectId()
    collection.insert_one.return_value.inserted_id = inserted_id

    result = repository.create({"name": "Sample"})

    inserted_document = collection.insert_one.call_args.args[0]

    assert inserted_document["org_id"] == "ORG001"
    assert result["_id"] == inserted_id


def test_create_rejects_different_tenant(repository, collection):
    with pytest.raises(ValueError):
        repository.create({
            "org_id": "ORG002",
            "name": "Cross tenant document",
        })

    collection.insert_one.assert_not_called()


def test_get_by_id_always_filters_by_tenant(repository, collection):
    document_id = str(ObjectId())

    repository.get_by_id(document_id)

    query = collection.find_one.call_args.args[0]

    assert query["org_id"] == "ORG001"
    assert query["_id"] == ObjectId(document_id)


def test_get_by_id_returns_none_for_foreign_tenant(repository, collection):
    document_id = str(ObjectId())
    collection.find_one.return_value = None

    result = repository.get_by_id(document_id)

    assert result is None
    collection.find_one.assert_called_once_with({
        "org_id": "ORG001",
        "_id": ObjectId(document_id),
    })


def test_list_cannot_override_tenant_filter(repository, collection):
    repository.list({"org_id": "ORG002"})

    query = collection.find.call_args.args[0]

    assert query == {
        "$and": [
            {"org_id": "ORG001"},
            {"org_id": "ORG002"},
        ]
    }


def test_update_by_id_always_filters_by_tenant(repository, collection):
    document_id = str(ObjectId())
    collection.update_one.return_value.matched_count = 1

    result = repository.update_by_id(
        document_id,
        {"status": "ACTIVE"},
    )

    query = collection.update_one.call_args.args[0]

    assert result is True
    assert query["org_id"] == "ORG001"


def test_update_returns_false_for_foreign_tenant_document(
    repository,
    collection,
):
    document_id = str(ObjectId())
    collection.update_one.return_value.matched_count = 0

    result = repository.update_by_id(
        document_id,
        {"status": "ACTIVE"},
    )

    assert result is False

    query = collection.update_one.call_args.args[0]
    assert query == {
        "org_id": "ORG001",
        "_id": ObjectId(document_id),
    }


def test_update_rejects_tenant_reassignment(repository, collection):
    with pytest.raises(ValueError):
        repository.update_by_id(
            str(ObjectId()),
            {"org_id": "ORG002"},
        )

    collection.update_one.assert_not_called()


def test_update_rejects_dotted_tenant_field(repository, collection):
    with pytest.raises(ValueError):
        repository.update_by_id(
            str(ObjectId()),
            {"org_id.value": "ORG002"},
        )

    collection.update_one.assert_not_called()


def test_delete_by_id_always_filters_by_tenant(repository, collection):
    document_id = str(ObjectId())
    collection.delete_one.return_value.deleted_count = 1

    result = repository.delete_by_id(document_id)

    query = collection.delete_one.call_args.args[0]

    assert result is True
    assert query["org_id"] == "ORG001"


def test_delete_returns_false_for_foreign_tenant_document(
    repository,
    collection,
):
    document_id = str(ObjectId())
    collection.delete_one.return_value.deleted_count = 0

    result = repository.delete_by_id(document_id)

    assert result is False

    query = collection.delete_one.call_args.args[0]
    assert query == {
        "org_id": "ORG001",
        "_id": ObjectId(document_id),
    }


def test_count_always_filters_by_tenant(repository, collection):
    collection.count_documents.return_value = 3

    result = repository.count({"status": "ACTIVE"})

    query = collection.count_documents.call_args.args[0]

    assert result == 3
    assert query == {
        "$and": [
            {"org_id": "ORG001"},
            {"status": "ACTIVE"},
        ]
    }
