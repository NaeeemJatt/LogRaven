# LogRaven — stream text lines through Logtest → NormalizedEvent list.

from __future__ import annotations

from app.config import settings
from app.integrations.decoder_manager.client import DecoderManagerClient
from app.integrations.decoder_manager.normalized_mapper import logtest_output_to_event
from app.parsers.normalizer import NormalizedEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def decode_text_file_to_events(
    file_path: str,
    *,
    log_format: str,
    location: str,
    source_type: str,
    max_lines: int | None = None,
) -> tuple[list[NormalizedEvent], dict]:
    """
    Send up to max_lines non-empty lines to the decoder manager.
    Returns (events, detail_dict).
    """
    cap = max_lines if max_lines is not None else settings.DECODER_MAX_LINES_PER_FILE
    lines: list[str] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                s = raw.rstrip("\n\r")
                if not s.strip():
                    continue
                lines.append(s)
                if len(lines) >= cap:
                    break
    except OSError as e:
        return [], {"error": str(e)[:200], "lines_processed": 0, "decoder_errors": 0}

    if not lines:
        return [], {"lines_processed": 0, "decoder_errors": 0, "note": "no_text_lines"}

    client = DecoderManagerClient()
    jwt = await client.authenticate()
    session_token: str | None = None
    events: list[NormalizedEvent] = []
    errors = 0

    try:
        for idx, line in enumerate(lines):
            try:
                session_token, output = await client.logtest_run(
                    token=session_token,
                    log_format=log_format,
                    location=location,
                    event=line,
                    jwt=jwt,
                )
                if output:
                    events.append(
                        logtest_output_to_event(
                            output=output,
                            source_type=source_type,
                            raw_line=line,
                            line_index=idx,
                        )
                    )
                else:
                    errors += 1
            except Exception as e:
                logger.debug("logtest line %s failed: %s", idx, e)
                errors += 1
    finally:
        if session_token:
            await client.delete_session(jwt, session_token)

    detail = {
        "lines_processed": len(lines),
        "decoder_errors": errors,
        "log_format": log_format,
        "location": location,
        "capped": len(lines) >= cap,
    }
    return events, detail
