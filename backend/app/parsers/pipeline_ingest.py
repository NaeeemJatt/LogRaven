# LogRaven — dual-path ingestion: native parsers vs decoder manager, with fallback.

from __future__ import annotations

import uuid
from typing import Any

from app.config import settings
from app.integrations.decoder_manager.format_resolver import resolve_log_format, synthetic_location
from app.integrations.decoder_manager.health import decoder_manager_is_healthy_cached
from app.integrations.decoder_manager.messages import (
    DECODER_MANAGER_UNAVAILABLE,
    DECODERS_NOT_APPLICABLE,
    FALLBACK_TO_DECODERS,
    FALLBACK_TO_PARSERS,
    user_message,
)
from app.integrations.decoder_manager.stream_decode import decode_text_file_to_events
from app.models.investigation_file import InvestigationFile
from app.parsers.detector import detect_candidates
from app.parsers.normalizer import NormalizedEvent
from app.parsers.quality import PARSE_QUALITY_SUFFICIENT, assess_parse_quality
from app.parsers.registry import PARSER_REGISTRY
from app.parsers.sniff import SniffResult, sniff_upload
from app.utils.logger import get_logger

logger = get_logger(__name__)

INGESTION_PARSERS = "parsers"
INGESTION_DECODERS = "decoders"


def try_native_parse(
    file_path_str: str,
    *,
    accept_low_quality: bool = False,
) -> tuple[list[NormalizedEvent] | None, str | None, dict[str, Any] | None, str | None]:
    """
    Run detector + registry parsers (same logic as investigation pipeline).
    Returns (events, log_type, detail, error). On success error is None.
    """
    parser_map = PARSER_REGISTRY
    try:
        candidates = detect_candidates(file_path_str)
        best_events: list[NormalizedEvent] | None = None
        best_cand = None
        best_quality_score = -1.0
        best_qr = None
        attempts: list[dict[str, Any]] = []

        for i, cand in enumerate(candidates[:4]):
            parser_cls = parser_map.get(cand.log_type)
            if parser_cls is None:
                attempts.append({"log_type": cand.log_type, "skipped": "no_parser"})
                continue
            try:
                evs = parser_cls().parse(file_path_str)
            except Exception as parse_exc:
                attempts.append(
                    {
                        "log_type": cand.log_type,
                        "error": str(parse_exc)[:200],
                        "events": 0,
                    }
                )
                continue
            qr = assess_parse_quality(evs)
            attempts.append(
                {
                    "log_type": cand.log_type,
                    "detection_confidence": cand.confidence,
                    "parse_quality": round(qr.score, 4),
                    "event_count": len(evs),
                }
            )
            if len(evs) == 0:
                continue
            if qr.score > best_quality_score:
                best_quality_score = qr.score
                best_events = evs
                best_cand = cand
                best_qr = qr
            if i == 0 and qr.score >= PARSE_QUALITY_SUFFICIENT:
                break

        if not best_events or best_cand is None:
            return None, None, {"attempts": attempts}, "Could not parse log file with any candidate parser"

        low_quality = (
            best_qr is not None
            and best_qr.score < PARSE_QUALITY_SUFFICIENT
            and len(best_events) >= 5
        )

        log_type = best_cand.log_type
        fallback_used = candidates[0].log_type != best_cand.log_type
        ranked_payload = [
            {"log_type": c.log_type, "confidence": c.confidence, "reasons": list(c.reasons)}
            for c in candidates
        ]
        detail = {
            "ranked_candidates": ranked_payload,
            "chosen_log_type": best_cand.log_type,
            "detection_confidence": best_cand.confidence,
            "parse_quality": round(best_qr.score, 4) if best_qr else None,
            "parse_warnings": list(best_qr.warnings) if best_qr else [],
            "fallback_used": fallback_used,
            "attempts": attempts,
            "native_low_quality": low_quality,
        }

        if low_quality and not accept_low_quality:
            return None, None, detail, "native_low_quality"

        return best_events, log_type, detail, None
    except Exception as e:
        logger.exception("native parse failed")
        return None, None, None, str(e)


async def _run_decoder_path(
    file_path_str: str,
    *,
    investigation_id: uuid.UUID,
    inv_file: InvestigationFile,
    sniff: SniffResult,
    max_lines: int | None = None,
) -> tuple[list[NormalizedEvent] | None, dict[str, Any], str | None]:
    """Returns (events, decode_detail, error)."""
    try:
        lf = resolve_log_format(
            source_type=inv_file.source_type,
            sniff=sniff,
            filename=inv_file.filename,
        )
        loc = synthetic_location(investigation_id, inv_file.filename)
        events, ddetail = await decode_text_file_to_events(
            file_path_str,
            log_format=lf,
            location=loc,
            source_type=inv_file.source_type,
            max_lines=max_lines,
        )
        ddetail["chosen_log_format"] = lf
        if not events:
            return None, ddetail, "decoder_zero_events"
        return events, ddetail, None
    except Exception as e:
        logger.warning("decoder path failed: %s", e)
        return None, {"error": str(e)[:300]}, str(e)


def _merge_detail(
    base: dict[str, Any],
    *,
    requested: str,
    actual: str,
    fallback_reason: str | None,
    warnings: list[str],
) -> dict[str, Any]:
    out = {**base}
    out["requested_ingestion_mode"] = requested
    out["actual_ingestion_path"] = actual
    out["fallback_reason"] = fallback_reason
    out["user_warnings"] = warnings
    return out


async def ingest_log_file(
    *,
    file_path_str: str,
    investigation_id: uuid.UUID,
    inv_file: InvestigationFile,
) -> tuple[list[NormalizedEvent], str, dict[str, Any]]:
    """
    Returns (events, log_type_for_ai, parser_selection_detail).
    log_type_for_ai is chosen_log_type or 'decoder' for decoder-primary path.
    """
    sniff = sniff_upload(file_path_str)
    requested = getattr(inv_file, "ingestion_mode", None) or INGESTION_PARSERS
    if requested not in (INGESTION_PARSERS, INGESTION_DECODERS):
        requested = INGESTION_PARSERS

    warnings: list[str] = []
    manager_ok = await decoder_manager_is_healthy_cached()

    # ── Decoders requested ───────────────────────────────────────────
    if requested == INGESTION_DECODERS:
        if sniff.is_pcap:
            raise ValueError("This file type is not supported.")
        if not sniff.decoder_eligible:
            ev, lt, det, err = try_native_parse(file_path_str, accept_low_quality=True)
            if not ev:
                raise ValueError(err or "Could not parse log file")
            detail = _merge_detail(
                det or {},
                requested=requested,
                actual=INGESTION_PARSERS,
                fallback_reason=DECODERS_NOT_APPLICABLE,
                warnings=[user_message(DECODERS_NOT_APPLICABLE)],
            )
            return ev, lt or "unknown", detail

        if not manager_ok:
            ev, lt, det, err = try_native_parse(file_path_str, accept_low_quality=True)
            if not ev:
                raise ValueError(err or "Could not parse log file")
            detail = _merge_detail(
                det or {},
                requested=requested,
                actual=INGESTION_PARSERS,
                fallback_reason=DECODER_MANAGER_UNAVAILABLE,
                warnings=[user_message(DECODER_MANAGER_UNAVAILABLE)],
            )
            return ev, lt or "unknown", detail

        ev_d, ddet, derr = await _run_decoder_path(
            file_path_str,
            investigation_id=investigation_id,
            inv_file=inv_file,
            sniff=sniff,
        )
        if ev_d:
            detail = _merge_detail(
                {"decoder_detail": ddet},
                requested=requested,
                actual=INGESTION_DECODERS,
                fallback_reason=None,
                warnings=[],
            )
            return ev_d, "decoder", detail

        ev, lt, det, err = try_native_parse(file_path_str, accept_low_quality=True)
        if not ev:
            raise ValueError(derr or err or "Could not parse log file")
        detail = _merge_detail(
            {**(det or {}), "decoder_detail": ddet},
            requested=requested,
            actual=INGESTION_PARSERS,
            fallback_reason=FALLBACK_TO_PARSERS,
            warnings=[user_message(FALLBACK_TO_PARSERS)],
        )
        return ev, lt or "unknown", detail

    # ── Parsers requested (default) ──────────────────────────────────
    ev, lt, det, err = try_native_parse(file_path_str)
    if ev:
        detail = _merge_detail(
            det or {},
            requested=requested,
            actual=INGESTION_PARSERS,
            fallback_reason=None,
            warnings=[],
        )
        return ev, lt or "unknown", detail

    # Native failed or low quality path returned error string
    if sniff.is_pcap:
        raise ValueError("This file type is not supported.")

    if manager_ok and sniff.decoder_eligible:
        ev_d, ddet, derr = await _run_decoder_path(
            file_path_str,
            investigation_id=investigation_id,
            inv_file=inv_file,
            sniff=sniff,
        )
        if ev_d:
            base = det or {"attempts": []}
            detail = _merge_detail(
                {**base, "decoder_detail": ddet},
                requested=requested,
                actual=INGESTION_DECODERS,
                fallback_reason=FALLBACK_TO_DECODERS,
                warnings=[user_message(FALLBACK_TO_DECODERS)],
            )
            return ev_d, "decoder", detail

    raise ValueError(
        err if err and err != "native_low_quality" else "Could not parse log file with any candidate parser"
    )
