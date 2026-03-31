# LogRaven — File Upload Validators

import mimetypes

from fastapi import UploadFile

from app.utils.exceptions import FileTooLargeError, InvalidFileTypeError

ALLOWED_EXTENSIONS = {"evtx", "csv", "log", "txt", "json"}

TIER_SIZE_LIMITS = {
    "free": 5 * 1024 * 1024,
    "pro": 50 * 1024 * 1024,
    "team": 200 * 1024 * 1024,
}

VALID_SOURCE_TYPES = {
    "windows_endpoint",
    "linux_endpoint",
    "firewall",
    "network",
    "web_server",
    "cloudtrail",
}

# Broad MIME allowlists per extension (content_type is advisory; extension is primary)
_EXT_MIME_OK = {
    "evtx": ("application/octet-stream", "application/x-ms-evtx"),
    "csv": ("text/csv", "text/plain", "application/csv", "application/vnd.ms-excel"),
    "log": ("text/plain", "application/octet-stream", "application/x-log"),
    "txt": ("text/plain", "application/octet-stream"),
    "json": ("application/json", "text/json", "text/plain"),
}


def _mime_matches_extension(ext: str, content_type: str) -> bool:
    ct = (content_type or "").split(";")[0].strip().lower()
    if not ct or ct == "application/octet-stream":
        return True
    allowed = _EXT_MIME_OK.get(ext, ())
    if ct in allowed:
        return True
    # Guess from filename — some clients send wrong MIME
    guess, _ = mimetypes.guess_type(f"x.{ext}")
    if guess and guess.lower() == ct:
        return True
    if ct == "application/octet-stream":
        return ext in ("evtx", "log", "txt")
    return False


async def validate_file_upload(file: UploadFile, tier: str) -> None:
    """
    Validate extension, rough MIME alignment, and size (streaming when size unknown).
    Raises InvalidFileTypeError or FileTooLargeError.
    """
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            f"File type .{ext or '?'} not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    if not _mime_matches_extension(ext, file.content_type or ""):
        raise InvalidFileTypeError(
            f"Content-Type does not match extension .{ext}. Got: {file.content_type or '(none)'}"
        )

    limit = TIER_SIZE_LIMITS.get(tier, TIER_SIZE_LIMITS["free"])

    if file.size is not None:
        if file.size > limit:
            raise FileTooLargeError(
                f"File exceeds size limit for your tier. Max: {limit // (1024 * 1024)} MB"
            )
        return

    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            await file.seek(0)
            raise FileTooLargeError(
                f"File exceeds size limit for your tier. Max: {limit // (1024 * 1024)} MB"
            )
    await file.seek(0)
