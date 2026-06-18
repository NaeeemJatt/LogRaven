# LogRaven — File Upload Validators

import mimetypes
import os
import re

from fastapi import UploadFile

from app.utils.exceptions import FileTooLargeError, InvalidFileTypeError

ALLOWED_EXTENSIONS = {"evtx", "csv", "log", "txt", "json"}

TIER_SIZE_LIMITS = {
    "free": 5 * 1024 * 1024,
    "pro": 50 * 1024 * 1024,
    "team": 200 * 1024 * 1024,
}

def sanitize_upload_filename(name: str, max_len: int = 200) -> str:
    """
    Single path segment safe for storage keys: no slashes, no traversal, no control chars.
    Preserves one extension when present.
    """
    base = os.path.basename((name or "").replace("\\", "/"))
    base = base.replace("\x00", "")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", base).strip("._")
    if not cleaned:
        cleaned = "upload"
    if "." in cleaned:
        stem, ext = cleaned.rsplit(".", 1)
        ext = ext[:32]
        stem = stem[: max(1, max_len - len(ext) - 1)] or "upload"
        cleaned = f"{stem}.{ext}"
    return cleaned[:max_len]


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


# Extensions whose real payload is binary; everything else must be UTF-8 text.
_BINARY_EXTENSIONS = {"evtx"}
# Magic-byte signatures keyed by extension (first bytes of a genuine file).
_MAGIC_SIGNATURES = {
    "evtx": b"ElfFile\x00",
}
# Bytes read from the start of the upload for content-based validation.
_CONTENT_SNIFF_BYTES = 8192


def _mime_matches_extension(ext: str, content_type: str) -> bool:
    ct = (content_type or "").split(";")[0].strip().lower()
    if not ct:
        return True
    # octet-stream is no longer a blanket pass: it is only acceptable for
    # extensions that can legitimately arrive as a generic binary stream.
    # The authoritative gate is _validate_content (magic bytes / UTF-8).
    if ct == "application/octet-stream":
        return ext in ("evtx", "log", "txt", "csv", "json")
    allowed = _EXT_MIME_OK.get(ext, ())
    if ct in allowed:
        return True
    # Guess from filename — some clients send wrong MIME
    guess, _ = mimetypes.guess_type(f"x.{ext}")
    if guess and guess.lower() == ct:
        return True
    return False


def _validate_content(ext: str, head: bytes) -> None:
    """
    Content-based gate: never trust the client-supplied extension/MIME alone.

    - Binary types (evtx) must start with their known magic signature.
    - Text types (csv/log/txt/json) must not contain NUL bytes in the head,
      which reliably indicates binary/polyglot content disguised as text.
    """
    if not head:
        return  # empty file — extension/size checks already ran

    signature = _MAGIC_SIGNATURES.get(ext)
    if signature is not None:
        if not head.startswith(signature):
            raise InvalidFileTypeError(
                f"File content does not match a valid .{ext} file."
            )
        return

    if ext not in _BINARY_EXTENSIONS and b"\x00" in head:
        raise InvalidFileTypeError(
            f"File content looks binary, not a valid text .{ext} file."
        )


async def validate_file_upload(
    file: UploadFile,
    tier: str,
    *,
    logical_filename: str | None = None,
) -> None:
    """
    Validate extension, rough MIME alignment, and size (streaming when size unknown).
    Raises InvalidFileTypeError or FileTooLargeError.
    *logical_filename* — use sanitized name for extension checks when uploads are renamed for storage.
    """
    filename = logical_filename or file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            f"File type .{ext or '?'} not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    if not _mime_matches_extension(ext, file.content_type or ""):
        raise InvalidFileTypeError(
            f"Content-Type does not match extension .{ext}. Got: {file.content_type or '(none)'}"
        )

    # Content-based validation (authoritative): sniff the file head, then rewind.
    head = await file.read(_CONTENT_SNIFF_BYTES)
    await file.seek(0)
    _validate_content(ext, head)

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
