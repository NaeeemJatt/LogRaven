# LogRaven — Resolve storage keys safely under a base directory (path traversal defense)

from pathlib import Path, PurePath

from fastapi import HTTPException, status


def resolved_file_under_storage_base(base: str | Path, storage_key: str) -> Path:
    """
    Join *storage_key* to *base* and resolve. Rejects keys that escape *base*
    (e.g. .., absolute paths, null bytes).
    """
    key = (storage_key or "").strip().replace("\x00", "")
    if not key or PurePath(key).is_absolute():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    base_p = Path(base).resolve()
    candidate = (base_p / key).resolve()
    try:
        candidate.relative_to(base_p)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return candidate
