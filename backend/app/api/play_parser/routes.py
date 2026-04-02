# LogRaven — PlayParser sandbox (parse + quality compare, no DB / Celery)

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.investigations.validators import sanitize_upload_filename, validate_file_upload
from app.config import settings
from app.dependencies import get_current_user
from app.limiter import limiter
from app.parsers.detector import detect_candidates
from app.parsers.normalizer import NormalizedEvent
from app.parsers.quality import assess_parse_quality
from app.parsers.registry import PARSER_KEYS, PARSER_REGISTRY
from app.schemas.play_parser import (
    PlayParserDetectCandidate,
    PlayParserDetectResponse,
    PlayParserEvaluateItem,
    PlayParserEvaluateResponse,
    PlayParserQuality,
    PlayParserSampleEvent,
)

router = APIRouter()


@router.get("/meta")
def play_parser_meta():
    """
    Public ping so you can verify the PlayParser router is mounted (GET /api/v1/play-parser/meta).
    If this 404s, the API process is missing the current codebase or is not the server you think.
    """
    return {"service": "play-parser", "endpoints": ["/evaluate", "/detect"]}


_MAX_PARSERS_PER_REQUEST = 5
_SAMPLE_EVENT_COUNT = 20
_RAW_MESSAGE_PREVIEW_MAX = 500


def _parse_parser_keys(parser_keys_json: str) -> list[str]:
    try:
        raw = json.loads(parser_keys_json)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"parser_keys must be valid JSON array: {e}",
        ) from e
    if not isinstance(raw, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parser_keys must be a JSON array of strings",
        )
    keys: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parser_keys must contain only strings",
            )
        k = item.strip()
        if k and k not in keys:
            keys.append(k)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one parser",
        )
    if len(keys) > _MAX_PARSERS_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At most {_MAX_PARSERS_PER_REQUEST} parsers per request",
        )
    unknown = [k for k in keys if k not in PARSER_REGISTRY]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown parser key(s): {unknown}. Allowed: {list(PARSER_KEYS)}",
        )
    return keys


def _normalized_event_to_sample(ev: NormalizedEvent) -> PlayParserSampleEvent:
    ts = ev.timestamp.isoformat() if ev.timestamp else None
    raw = (ev.raw_message or "")[:_RAW_MESSAGE_PREVIEW_MAX]
    return PlayParserSampleEvent(
        timestamp=ts,
        source_type=ev.source_type,
        hostname=ev.hostname,
        username=ev.username,
        source_ip=ev.source_ip,
        event_type=ev.event_type,
        event_id=ev.event_id,
        raw_message=raw,
        severity_hint=ev.severity_hint or "informational",
    )


@router.post("/evaluate", response_model=PlayParserEvaluateResponse)
@limiter.limit("30/hour")
async def evaluate_parsers(
    request: Request,
    file: UploadFile = File(...),
    parser_keys: str = Form(..., description='JSON array, e.g. ["syslog","nginx"]'),
    current_user=Depends(get_current_user),
):
    """
    Upload one log file and run the selected parsers; returns per-parser quality heuristics
    and a capped preview of normalized events. Does not persist investigations.
    """
    keys = _parse_parser_keys(parser_keys)
    filename = sanitize_upload_filename(file.filename or "upload")
    await validate_file_upload(file, current_user.tier, logical_filename=filename)

    base = Path(settings.LOCAL_STORAGE_PATH) / "playground" / str(current_user.id)
    base.mkdir(parents=True, exist_ok=True)
    tmp_path = base / f"{uuid.uuid4()}_{filename}"

    try:
        with open(tmp_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    path_str = str(tmp_path)
    results: list[PlayParserEvaluateItem] = []
    max_ev = settings.MAX_PARSED_EVENTS_PER_FILE

    try:
        for key in keys:
            try:
                events = PARSER_REGISTRY[key]().parse(path_str)
            except Exception as e:
                msg = str(e).strip() or type(e).__name__
                results.append(
                    PlayParserEvaluateItem(
                        parser_key=key,
                        ok=False,
                        event_count=0,
                        error=msg[:500],
                    )
                )
                continue

            trimmed = len(events) > max_ev
            work_events = events[:max_ev] if trimmed else events
            q = assess_parse_quality(work_events)
            warn = list(q.warnings)
            if trimmed:
                warn.append("trimmed_for_evaluation")

            samples = [_normalized_event_to_sample(e) for e in work_events[:_SAMPLE_EVENT_COUNT]]
            sample_payload = samples if samples else None

            results.append(
                PlayParserEvaluateItem(
                    parser_key=key,
                    ok=True,
                    event_count=len(work_events),
                    events_trimmed=trimmed,
                    quality=PlayParserQuality(
                        score=q.score,
                        valid_timestamp_ratio=q.valid_timestamp_ratio,
                        structured_ratio=q.structured_ratio,
                        warnings=warn,
                    ),
                    sample_events=sample_payload,
                )
            )
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass

    return PlayParserEvaluateResponse(results=results)


@router.post("/detect", response_model=PlayParserDetectResponse)
@limiter.limit("60/hour")
async def detect_log_type(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Read-only detector hints (same head scan as investigations). Does not parse with pipeline parsers.
    """
    filename = sanitize_upload_filename(file.filename or "upload")
    await validate_file_upload(file, current_user.tier, logical_filename=filename)

    base = Path(settings.LOCAL_STORAGE_PATH) / "playground" / str(current_user.id)
    base.mkdir(parents=True, exist_ok=True)
    tmp_path = base / f"{uuid.uuid4()}_{filename}"

    try:
        with open(tmp_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    try:
        candidates = detect_candidates(str(tmp_path))
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass

    out = [
        PlayParserDetectCandidate(
            log_type=c.log_type,
            confidence=c.confidence,
            reasons=list(c.reasons),
        )
        for c in candidates
    ]
    return PlayParserDetectResponse(candidates=out)
