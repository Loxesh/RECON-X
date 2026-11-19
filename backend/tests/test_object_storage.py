
from pathlib import Path

import pytest

from app.integrations.object_storage import LocalPrivateObjectStorage


def test_object_is_stored_inside_private_directory(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)

    storage.put_object(
        key="ORG001/2026/11/file123/original",
        content=b"private financial data",
        content_type="text/csv",
    )

    stored_file = (
        tmp_path
        / "ORG001"
        / "2026"
        / "11"
        / "file123"
        / "original"
    )

    assert stored_file.exists()
    assert stored_file.read_bytes() == b"private financial data"


def test_object_can_be_deleted(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)
    key = "ORG001/2026/11/file123/original"

    storage.put_object(
        key=key,
        content=b"sample",
        content_type="text/csv",
    )

    storage.delete_object(key)

    assert not (
        tmp_path
        / "ORG001"
        / "2026"
        / "11"
        / "file123"
        / "original"
    ).exists()


@pytest.mark.parametrize(
    "key",
    [
        "../outside.txt",
        "/outside.txt",
        r"ORG001\..\outside.txt",
        "",
    ],
)
def test_path_traversal_keys_are_rejected(tmp_path, key):
    storage = LocalPrivateObjectStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.put_object(
            key=key,
            content=b"data",
            content_type="text/plain",
        )


def test_existing_object_is_not_overwritten(tmp_path):
    storage = LocalPrivateObjectStorage(tmp_path)
    key = "ORG001/2026/11/file123/original"

    storage.put_object(key, b"original", "text/csv")

    with pytest.raises(FileExistsError):
        storage.put_object(key, b"replacement", "text/csv")

    stored_file = (
        tmp_path
        / "ORG001"
        / "2026"
        / "11"
        / "file123"
        / "original"
    )

    assert stored_file.read_bytes() == b"original"
