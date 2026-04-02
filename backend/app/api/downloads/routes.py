# LogRaven — Signed file downloads (local storage; no public /files/ mount)

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings
from app.dependencies import get_current_user
from app.utils.security import decode_file_download_token
from app.utils.storage_paths import resolved_file_under_storage_base

router = APIRouter()


@router.get("/file")
async def download_file_with_token(
    token: str = Query(..., min_length=20),
    current_user=Depends(get_current_user),
):
    if settings.STORAGE_BACKEND != "local":
        raise HTTPException(status_code=404, detail="Not found")

    storage_key, owner_uid = decode_file_download_token(token)
    if str(current_user.id) != owner_uid:
        raise HTTPException(status_code=403, detail="Not allowed to download this file")

    path = resolved_file_under_storage_base(settings.LOCAL_STORAGE_PATH, storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        filename=path.name,
        media_type="application/pdf",
    )
