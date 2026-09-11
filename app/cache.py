from __future__ import annotations

from pathlib import Path


def dataset_version(path: str | Path) -> tuple[int, int]:
    """Return a filesystem version key that changes when a published DB changes."""
    stat = Path(path).stat()
    return stat.st_mtime_ns, stat.st_size
