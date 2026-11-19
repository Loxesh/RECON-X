
"""Private object-storage interface and local development adapter."""

from pathlib import Path
from typing import Protocol
import os


class ObjectStorage(Protocol):
    """Provider-independent object storage contract."""

    def put_object(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        ...

    def delete_object(self, key: str) -> None:
        ...


class LocalPrivateObjectStorage:
    """Private filesystem storage for local development."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        """Resolve a key without allowing path traversal."""

        if not key or "\\" in key or key.startswith("/"):
            raise ValueError("Invalid storage key.")

        parts = Path(key).parts

        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Invalid storage key.")

        destination = (self.root / Path(*parts)).resolve()

        if not destination.is_relative_to(self.root):
            raise ValueError("Storage key escapes the private storage root.")

        return destination

    def put_object(
        self,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        """Store an original file without exposing a public URL."""

        destination = self._resolve_key(key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(str(destination), flags, 0o600)

        try:
            with os.fdopen(descriptor, "wb") as file:
                file.write(content)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def delete_object(self, key: str) -> None:
        """Remove a stored object during failed upload cleanup."""

        destination = self._resolve_key(key)
        destination.unlink(missing_ok=True)
