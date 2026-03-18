"""Create metadata + artifact backend from ``database_url``."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ascp.config import Settings


def create_backend(settings: "Settings") -> Any:
    url = (settings.database_url or "").strip()
    root = Path(settings.artifact_root)
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        from ascp.storage.postgres_fs import PostgresFsBackend

        return PostgresFsBackend(url, root)
    from ascp.storage.sqlite_fs import SqliteFsBackend

    return SqliteFsBackend(url, root)
