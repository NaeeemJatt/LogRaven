# LogRaven — PlayParser sandbox (parse + quality compare, no DB / Celery)

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.investigations.validators import (
    VALID_SOURCE_TYPES,
    sanitize_upload_filename,
    validate_file_upload,
)
from app.config import settings
from app.dependencies import get_current_user
from app.integrations.decoder_manager.format_resolver import resolve_log_format, synthetic_location
from app.integrations.decoder_manager.health import decoder_manager_is_healthy_cached
from app.integrations.decoder_manager.messages import (
    DECODER_MANAGER_UNAVAILABLE,
    DECODERS_NOT_APPLICABLE,
    user_message,
)
from app.integrations.decoder_manager.stream_decode import decode_text_file_to_events
from app.limiter import limiter
from app.parsers.compare_outputs import compare_event_streams
from app.parsers.detector import detect_candidates
from app.parsers.line_align import build_preview_rows_for_decoder, build_preview_rows_for_parser
from app.parsers.normalizer import NormalizedEvent
from app.parsers.quality import assess_parse_quality
from app.parsers.registry import PARSER_KEYS, PARSER_REGISTRY
from app.parsers.sniff import sniff_upload
from app.parsers.text_lines import read_first_nonblank_lines
from app.schemas.play_parser import (
    PlayDecoderSummary,
    PlayParserCompareMetrics,
    PlayParserDetectCandidate,
    PlayParserDetectResponse,
    PlayParserEvaluateCompareResponse,
    PlayParserEvaluateItem,
    PlayParserEvaluateResponse,
    PlayParserPreviewResponse,
    PlayParserPreviewRow,
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
    return {"service": "play-parser", "endpoints": ["/evaluate", "/evaluate-compare", "/preview", "/detect"]}


_MAX_PARSERS_PER_REQUEST = 5
_SAMPLE_EVENT_COUNT = 20
_RAW_MESSAGE_PREVIEW_MAX = 500
_PLAY_INV_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
_PREVIEW_TARGET_DECODER = "decoder"


def _parse_parser_keys(parser_keys_json: str, *, allow_empty: bool = False) -> list[str]:
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
        if allow_empty:
            return []
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


def _truthy_form(v: str) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


@router.post("/evaluate-compare", response_model=PlayParserEvaluateCompareResponse)
@limiter.limit("20/hour")
async def evaluate_compare(
    request: Request,
    file: UploadFile = File(...),
    parser_keys: str = Form(..., description='JSON array; may be [] when play_mode=decoders_only'),
    source_type: str = Form("linux_endpoint"),
    include_decoders: str = Form("true"),
    play_mode: str = Form("both"),
    current_user=Depends(get_current_user),
):
    """
    Run parsers and/or decoders. play_mode: parsers_only | decoders_only | both.
    decoders_only allows parser_keys=[].
    """
    pm = (play_mode or "both").strip().lower()
    if pm not in ("parsers_only", "decoders_only", "both"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="play_mode must be parsers_only, decoders_only, or both",
        )

    keys = _parse_parser_keys(parser_keys, allow_empty=(pm == "decoders_only"))
    st = (source_type or "linux_endpoint").strip()
    if st not in VALID_SOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type. Must be one of: {sorted(VALID_SOURCE_TYPES)}",
        )

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
    max_ev = settings.MAX_PARSED_EVENTS_PER_FILE
    parser_results: list[PlayParserEvaluateItem] = []
    native_best: list[NormalizedEvent] | None = None
    decoder_events_out: list[NormalizedEvent] | None = None

    run_parsers = pm in ("parsers_only", "both")
    want_dec = pm == "decoders_only" or (pm == "both" and _truthy_form(include_decoders))

    try:
        if run_parsers:
            for key in keys:
                try:
                    events = PARSER_REGISTRY[key]().parse(path_str)
                except Exception as e:
                    msg = str(e).strip() or type(e).__name__
                    parser_results.append(
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
                parser_results.append(
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
                        sample_events=samples if samples else None,
                    )
                )
                if native_best is None or len(work_events) > len(native_best):
                    native_best = work_events

        dec_summary = PlayDecoderSummary(ok=False, manager_reachable=False)
        compare_metrics: PlayParserCompareMetrics | None = None

        if want_dec:
            mgr = await decoder_manager_is_healthy_cached()
            dec_summary.manager_reachable = mgr
            sniff = sniff_upload(path_str)
            if not mgr:
                dec_summary.warning_codes = [DECODER_MANAGER_UNAVAILABLE]
                dec_summary.user_messages = [user_message(DECODER_MANAGER_UNAVAILABLE)]
            elif not sniff.decoder_eligible:
                dec_summary.warning_codes = [DECODERS_NOT_APPLICABLE]
                dec_summary.user_messages = [user_message(DECODERS_NOT_APPLICABLE)]
            else:
                try:
                    lf = resolve_log_format(source_type=st, sniff=sniff, filename=filename)
                    loc = synthetic_location(_PLAY_INV_ID, filename)
                    devents, ddet = await decode_text_file_to_events(
                        path_str,
                        log_format=lf,
                        location=loc,
                        source_type=st,
                        max_lines=settings.DECODER_PLAY_MAX_LINES,
                    )
                    cap = settings.DECODER_PLAY_MAX_LINES
                    trimmed_d = ddet.get("lines_processed", 0) >= cap
                    decoder_events_out = devents
                    if devents:
                        dec_summary.ok = True
                        dec_summary.event_count = len(devents)
                        dec_summary.events_trimmed = trimmed_d
                        dec_summary.sample_events = [
                            _normalized_event_to_sample(e) for e in devents[:_SAMPLE_EVENT_COUNT]
                        ]
                    else:
                        dec_summary.error = "Decoder path produced no events."
                except Exception as e:
                    dec_summary.error = (str(e) or type(e).__name__)[:500]

        if (
            decoder_events_out
            and native_best
            and len(native_best) > 0
            and len(decoder_events_out) > 0
        ):
            m = compare_event_streams(native_best[:max_ev], decoder_events_out, sample_limit=20)
            compare_metrics = PlayParserCompareMetrics(**m)

        return PlayParserEvaluateCompareResponse(
            parser_results=parser_results,
            decoders=dec_summary,
            compare=compare_metrics,
        )
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


@router.post("/preview", response_model=PlayParserPreviewResponse)
@limiter.limit("40/hour")
async def play_parser_preview(
    request: Request,
    file: UploadFile = File(...),
    preview_target: str = Form(..., description='Parser key or "decoder"'),
    source_type: str = Form("linux_endpoint"),
    line_limit: int = Form(50),
    current_user=Depends(get_current_user),
):
    """
    First N non-blank lines with raw vs parsed fields (native parser or decoder path).
    """
    target = (preview_target or "").strip()
    if not target:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="preview_target is required")

    eff = max(1, min(int(line_limit), settings.PLAY_PARSER_PREVIEW_MAX_LINES))

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
    raw_cap = settings.PLAY_PARSER_PREVIEW_RAW_MAX_CHARS

    try:
        if target == _PREVIEW_TARGET_DECODER:
            st = (source_type or "linux_endpoint").strip()
            if st not in VALID_SOURCE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid source_type. Must be one of: {sorted(VALID_SOURCE_TYPES)}",
                )
            decode_cap = min(eff, settings.DECODER_PLAY_MAX_LINES)
            lines = read_first_nonblank_lines(path_str, decode_cap)
            mgr = await decoder_manager_is_healthy_cached()
            if not mgr:
                return PlayParserPreviewResponse(
                    preview_kind="decoder",
                    key=_PREVIEW_TARGET_DECODER,
                    line_limit=eff,
                    rows=[],
                    note=user_message(DECODER_MANAGER_UNAVAILABLE),
                )
            sniff = sniff_upload(path_str)
            if not sniff.decoder_eligible:
                return PlayParserPreviewResponse(
                    preview_kind="decoder",
                    key=_PREVIEW_TARGET_DECODER,
                    line_limit=eff,
                    rows=[],
                    note=user_message(DECODERS_NOT_APPLICABLE),
                )
            try:
                lf = resolve_log_format(source_type=st, sniff=sniff, filename=filename)
                loc = synthetic_location(_PLAY_INV_ID, filename)
                devents, _ddet = await decode_text_file_to_events(
                    path_str,
                    log_format=lf,
                    location=loc,
                    source_type=st,
                    max_lines=decode_cap,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(str(e) or type(e).__name__)[:500],
                ) from e
            row_dicts = build_preview_rows_for_decoder(lines, devents, raw_max_chars=raw_cap)
            rows = [PlayParserPreviewRow(**r) for r in row_dicts]
            return PlayParserPreviewResponse(
                preview_kind="decoder",
                key=_PREVIEW_TARGET_DECODER,
                line_limit=eff,
                rows=rows,
                note=None,
            )

        if target not in PARSER_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown preview_target. Use a parser key or {_PREVIEW_TARGET_DECODER!r}. Allowed parsers: {list(PARSER_KEYS)}",
            )

        lines = read_first_nonblank_lines(path_str, eff)
        try:
            events = PARSER_REGISTRY[target]().parse(path_str)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(str(e) or type(e).__name__)[:500],
            ) from e

        row_dicts = build_preview_rows_for_parser(lines, events, raw_max_chars=raw_cap)
        rows = [PlayParserPreviewRow(**r) for r in row_dicts]
        return PlayParserPreviewResponse(
            preview_kind="parser",
            key=target,
            line_limit=eff,
            rows=rows,
            note=None,
        )
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


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
