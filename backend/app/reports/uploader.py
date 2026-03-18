# LogRaven — Report Uploader

import os

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def upload_report(pdf_path: str, investigation_id, storage) -> str:
    """
    Move a generated PDF from local temp storage to permanent report storage.

    Args:
        pdf_path:         Absolute local path to the PDF file.
        investigation_id: UUID of the investigation.
        storage:          StorageBackend instance.

    Returns:
        Storage key (e.g. "reports/{id}/lograven-report-abcd1234.pdf").
    """
    filename = os.path.basename(pdf_path)
    key = f"reports/{investigation_id}/{filename}"

    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()

    await storage.save_file_from_bytes(key, pdf_bytes)
    logger.info("LogRaven uploader: stored PDF at key=%s", key)

    # Clean up temp file after successful upload
    try:
        os.remove(pdf_path)
    except OSError as e:
        logger.warning("LogRaven uploader: could not delete temp PDF %s: %s", pdf_path, e)

    return key
