# LogRaven — Main Investigation Processing Task

import hashlib
import os
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from collections import Counter
from datetime import datetime

from sqlalchemy import delete, select, text
from sqlalchemy.orm import selectinload

from app.tasks.async_runner import run_async
from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger("lograven.pipeline")

_SEP = "─" * 55
_LOCK_RETRY_MAX = 6
_LOCK_RETRY_MAX_DELAY_SECONDS = 8


async def _commit_progress(db, investigation, stage: str, *, status: str | None = None) -> None:
    """Persist progress so GET /status polling shows live pipeline position."""
    if status is not None:
        investigation.status = status
    investigation.progress_stage = stage
    await db.commit()


def _banner(stage: str) -> None:
    logger.info(_SEP)
    logger.info("  ▶  %s", stage)
    logger.info(_SEP)


def _should_run_correlation(correlation_enabled: bool, file_events_map: dict[str, list]) -> bool:
    return correlation_enabled and len(file_events_map) >= 2


def _build_source_labels(files: list) -> dict[str, str]:
    """Use filenames normally and disambiguate duplicates with stable file IDs."""
    filename_counts = Counter(file.filename for file in files)
    return {
        str(file.id): (
            f"{file.filename} [{str(file.id)[:8]}]"
            if filename_counts[file.filename] > 1
            else file.filename
        )
        for file in files
    }


def _finding_identity(finding: dict) -> tuple[str, str, str, tuple[str, ...]]:
    title = " ".join(str(finding.get("title") or "").split()).casefold()
    technique = str(finding.get("mitre_technique_id") or "").strip().upper()
    finding_type = str(finding.get("finding_type") or "single").strip().casefold()
    source_files = tuple(sorted(
        str(source).strip().casefold()
        for source in (finding.get("source_files") or [])
    ))
    return title, technique, finding_type, source_files


def _merge_rule_and_ai_findings(
    rule_findings: list[dict],
    ai_single_findings: list[dict],
    ai_correlated_findings: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Keep deterministic findings first and suppress exact AI duplicates."""
    rule_identities = {_finding_identity(finding) for finding in rule_findings}
    single = rule_findings + [
        finding
        for finding in ai_single_findings
        if _finding_identity(finding) not in rule_identities
    ]
    return single, ai_correlated_findings


def _build_report_summary(single_findings: list[dict], correlated_findings: list[dict]) -> str:
    individual_label = "finding" if len(single_findings) == 1 else "findings"
    correlated_label = "finding" if len(correlated_findings) == 1 else "findings"
    return (
        f"Analysis complete. Found {len(single_findings)} individual {individual_label} "
        f"and {len(correlated_findings)} correlated {correlated_label}."
    )


async def _upsert_report_and_findings(
    db,
    *,
    investigation,
    single_findings: list[dict],
    correlated_findings: list[dict],
    severity_counts: dict,
    mitre_techniques: list[str],
    parsed_source_files: list[str],
    correlated_source_files: list[str],
):
    """Replace one investigation report and its findings under a row lock."""
    from app.models.finding import Finding
    from app.models.investigation import Investigation
    from app.models.report import Report

    await db.execute(
        select(Investigation.id)
        .where(Investigation.id == investigation.id)
        .with_for_update()
    )
    result = await db.execute(
        select(Report).where(Report.investigation_id == investigation.id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        report = Report(
            investigation_id=investigation.id,
            user_id=investigation.user_id,
        )
        db.add(report)
        await db.flush()
    else:
        await db.execute(delete(Finding).where(Finding.report_id == report.id))
        report.pdf_storage_key = None

    report.summary = _build_report_summary(single_findings, correlated_findings)
    report.severity_counts = severity_counts
    report.correlated_findings = correlated_findings
    report.single_source_findings = single_findings
    report.mitre_techniques = mitre_techniques
    report.created_at = datetime.utcnow()

    for finding_dict in single_findings + correlated_findings:
        is_correlated = finding_dict.get("finding_type") == "correlated"
        db.add(Finding(
            report_id=report.id,
            severity=finding_dict.get("severity", "informational"),
            title=(finding_dict.get("title") or "")[:300],
            description=finding_dict.get("description", ""),
            mitre_technique_id=finding_dict.get("mitre_technique_id"),
            mitre_technique_name=finding_dict.get("mitre_technique_name"),
            mitre_tactic=finding_dict.get("mitre_tactic"),
            iocs=finding_dict.get("iocs", []),
            remediation=finding_dict.get("remediation"),
            finding_type=finding_dict.get(
                "finding_type",
                "correlated" if is_correlated else "single",
            ),
            confidence=float(finding_dict.get("confidence", 0.8)),
            source_files=(
                finding_dict.get("source_files")
                or (correlated_source_files if is_correlated else parsed_source_files)
            ),
        ))

    await db.flush()
    return report


def _advisory_lock_key(investigation_id: str) -> int:
    """Derive one stable signed PostgreSQL bigint key from the full UUID."""
    digest = hashlib.blake2b(
        uuid.UUID(str(investigation_id)).bytes,
        digest_size=8,
        person=b"lograven-job",
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


@asynccontextmanager
async def _pipeline_execution_guard(
    investigation_id: str,
    *,
    connection_factory=None,
):
    """Hold a session advisory lock on one dedicated connection."""
    if connection_factory is None:
        from app.dependencies import engine

        connection_factory = engine.connect

    key = _advisory_lock_key(investigation_id)
    async with connection_factory() as connection:
        acquired = False
        try:
            result = await connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": key},
            )
            acquired = bool(result.scalar_one())
            # Session locks survive commit; close the short acquisition
            # transaction so the dedicated connection is not idle-in-transaction.
            await connection.commit()
            yield acquired
        finally:
            if acquired:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": key},
                )
                await connection.commit()


async def _run_pipeline_guarded(
    investigation_id: str,
    *,
    cloud_ai_consent: bool = False,
    guard_factory=None,
    pipeline_runner=None,
) -> bool:
    """Run the inner pipeline only while this process owns its DB session lock."""
    guard_factory = guard_factory or _pipeline_execution_guard
    pipeline_runner = pipeline_runner or _run_pipeline

    async with guard_factory(investigation_id) as acquired:
        if not acquired:
            logger.info(
                "Pipeline already active for investigation %s; skipping duplicate delivery",
                investigation_id,
            )
            return False
        await pipeline_runner(
            investigation_id,
            cloud_ai_consent=cloud_ai_consent,
        )
        return True


@celery_app.task(
    name="process_investigation",
    bind=True,
    max_retries=_LOCK_RETRY_MAX,
)
def process_investigation(self, investigation_id: str, cloud_ai_consent: bool = False):
    acquired = run_async(
        _run_pipeline_guarded(
            investigation_id,
            cloud_ai_consent=cloud_ai_consent,
        )
    )
    if not acquired:
        retry_number = getattr(self.request, "retries", 0)
        countdown = min(
            2 ** retry_number,
            _LOCK_RETRY_MAX_DELAY_SECONDS,
        )
        raise self.retry(
            exc=RuntimeError("Investigation pipeline lock is currently held"),
            countdown=countdown,
        )


async def _run_pipeline(investigation_id: str, *, cloud_ai_consent: bool = False) -> None:  # noqa: C901
    from app.dependencies import AsyncSessionLocal
    from app.models.finding import Finding
    from app.models.investigation import Investigation
    from app.models.user import User
    from app.config import settings
    from app.utils.storage import create_storage_backend

    storage = create_storage_backend()

    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  LogRaven Pipeline  »  investigation: %s  ║", str(investigation_id)[:8])
    logger.info("╚══════════════════════════════════════════════════════╝")

    async with AsyncSessionLocal() as db:
        try:
            # ── Step 1: Fetch ─────────────────────────────────────────────────
            _banner("STEP 1 / 7  —  Fetch Investigation")
            result = await db.execute(
                select(Investigation)
                .options(selectinload(Investigation.files))
                .where(Investigation.id == investigation_id)
            )
            investigation = result.scalar_one_or_none()
            if investigation is None:
                logger.error("Investigation %s not found in DB", investigation_id)
                return
            if investigation.status == "complete":
                logger.info("Investigation %s is already complete; skipping redelivery", investigation_id)
                return
            if investigation.status not in ("queued", "processing"):
                logger.warning(
                    "Investigation %s has status %s; skipping pipeline delivery",
                    investigation_id,
                    investigation.status,
                )
                return

            logger.info("  name  : %s", investigation.name)
            logger.info("  files : %d", len(investigation.files))

            from app.ai.cloud.consent import cloud_ai_enabled, require_cloud_ai_consent

            try:
                require_cloud_ai_consent(cloud_ai_consent)
            except Exception:
                investigation.progress_stage = "ai_analysis"
                await db.commit()
                raise

            # ── Step 2: Mark processing ───────────────────────────────────────
            await _commit_progress(db, investigation, "parsing", status="processing")

            all_events = []
            primary_log_type: str | None = None
            file_events_map: dict[str, list] = {}   # keyed by stable investigation-file ID
            event_source_files: dict[int, str] = {}
            source_labels = _build_source_labels(investigation.files)

            # ── Step 3: Parse files ───────────────────────────────────────────
            _banner("STEP 2 / 7  —  Parse Log Files")
            from app.parsers.pipeline_ingest import ingest_log_file

            for inv_file in investigation.files:
                logger.info("  file  : %s", inv_file.filename)
                try:
                    file_path = await storage.get_file_path(inv_file.storage_key)
                    file_path_str = str(file_path)
                    try:
                        events, log_type, detail = await ingest_log_file(
                            file_path_str=file_path_str,
                            investigation_id=investigation.id,
                            inv_file=inv_file,
                        )

                        inv_file.log_type = log_type
                        inv_file.parser_selection_detail = detail
                        conf = detail.get("detection_confidence")
                        inv_file.parser_detection_confidence = (
                            float(conf) if isinstance(conf, (int, float)) else None
                        )
                        await db.commit()
                        logger.info(
                            "  type  : %s  →  [%s] requested=%s actual=%s",
                            inv_file.filename,
                            log_type,
                            detail.get("requested_ingestion_mode"),
                            detail.get("actual_ingestion_path"),
                        )

                        if primary_log_type is None:
                            primary_log_type = log_type
                        if len(events) > settings.MAX_PARSED_EVENTS_PER_FILE:
                            raise ValueError(
                                f"Parsed event count exceeded per-file security cap "
                                f"({settings.MAX_PARSED_EVENTS_PER_FILE})"
                            )

                        next_total = len(all_events) + len(events)
                        if next_total > settings.MAX_PARSED_EVENTS_PER_INVESTIGATION:
                            raise ValueError(
                                "Parsed event volume exceeded investigation security cap "
                                f"({settings.MAX_PARSED_EVENTS_PER_INVESTIGATION})"
                            )

                        file_id = str(inv_file.id)
                        source_label = source_labels[file_id]
                        for ev in events:
                            ev.source_type = inv_file.source_type
                            event_source_files[id(ev)] = source_label

                        inv_file.status = "parsed"
                        inv_file.event_count = len(events)
                        inv_file.parsed_at = datetime.utcnow()
                        await db.commit()
                        logger.info("  parsed: %d events from %s", len(events), inv_file.filename)
                        all_events.extend(events)
                        file_events_map[file_id] = events
                    finally:
                        if settings.STORAGE_BACKEND == "s3":
                            Path(file_path_str).unlink(missing_ok=True)

                except Exception as file_exc:
                    logger.error("  ERROR parsing %s: %s", inv_file.filename, file_exc, exc_info=True)
                    inv_file.status = "failed"
                    inv_file.error_message = str(file_exc)[:500]
                    await db.commit()

            logger.info("  total : %d events across %d file(s)", len(all_events), len(investigation.files))

            await _commit_progress(db, investigation, "rule_engine")

            # ── Step 4: Rule engine ───────────────────────────────────────────
            _banner("STEP 3 / 7  —  Rule Engine")
            rule_findings: list[dict] = []
            try:
                from app.rules.engine import rule_matches_to_findings, run_rules_with_matches

                before = len(all_events)
                all_events, rule_matches = run_rules_with_matches(all_events)
                rule_findings = rule_matches_to_findings(rule_matches, event_source_files)
                flagged = sum(1 for e in all_events if e.flags)
                logger.info("  events : %d in → %d out", before, len(all_events))
                logger.info("  flagged: %d events have detection flags", flagged)
                logger.info("  rules  : %d deterministic findings", len(rule_findings))
            except Exception as e:
                logger.warning("  rule engine error (skipping): %s", e)

            await _commit_progress(db, investigation, "correlation")

            # ── Step 5: Correlation ───────────────────────────────────────────
            _banner("STEP 4 / 7  —  Correlation Engine")
            correlation_summary: list = []
            try:
                if _should_run_correlation(investigation.correlation_enabled, file_events_map):
                    from app.correlation.engine import correlate
                    correlation_summary = correlate(
                        str(investigation.id), file_events_map
                    )
                    chains_count = len(correlation_summary) if isinstance(correlation_summary, list) else 0
                    logger.info("  chains : %d cross-source chains found", chains_count)
                else:
                    logger.info("  skipped (disabled or fewer than 2 parsed files)")
            except Exception as e:
                logger.warning("  correlation error (skipping): %s", e)

            await _commit_progress(db, investigation, "ai_analysis")

            # ── Step 6: AI ceiling ────────────────────────────────────────────
            user_result = await db.execute(select(User).where(User.id == investigation.user_id))
            user = user_result.scalar_one_or_none()
            tier = user.tier if user else "free"

            events_for_ai = all_events
            try:
                from app.ai.cost_limiter import enforce_ceiling
                events_for_ai, was_truncated = enforce_ceiling(all_events, tier)
                if was_truncated:
                    logger.info("  ceiling: %d → %d events (tier=%s, truncated)",
                        len(all_events), len(events_for_ai), tier)
                else:
                    logger.info("  ceiling: %d events within limit (tier=%s)",
                        len(events_for_ai), tier)
            except Exception as e:
                logger.warning("  cost limiter error (skipping): %s", e)

            # ── Step 7: AI analysis ───────────────────────────────────────────
            _banner("STEP 5 / 7  —  AI Analysis")
            ai_single_findings: list[dict] = []
            ai_correlated_findings: list[dict] = []
            chains = correlation_summary if isinstance(correlation_summary, list) else []

            ai_log_type = primary_log_type if (len(investigation.files) == 1 and primary_log_type) else "mixed"
            logger.info("  engine : LogRaven AI")
            logger.info("  type   : %s  |  events: %d  |  chains: %d",
                ai_log_type, len(events_for_ai), len(chains))

            if cloud_ai_enabled():
                try:
                    from app.ai.router import route_analysis

                    ai_single_findings, ai_correlated_findings = await route_analysis(
                        events_for_ai, ai_log_type, chains, tier
                    )
                    logger.info("  single : %d findings", len(ai_single_findings))
                    logger.info("  correl : %d findings", len(ai_correlated_findings))
                except Exception as e:
                    logger.error("  AI error (continuing): %s", e, exc_info=True)
            else:
                logger.info("  skipped (no cloud AI provider configured)")

            await _commit_progress(db, investigation, "building_report")

            # ── MITRE enrichment ──────────────────────────────────────────────
            _banner("STEP 6 / 7  —  MITRE ATT&CK Enrichment")
            try:
                from app.reports.mitre_mapper import enrich_all

                rule_findings = enrich_all(rule_findings)
                ai_single_findings = enrich_all(ai_single_findings)
                ai_correlated_findings = enrich_all(ai_correlated_findings)
                techniques = {
                    finding.get("mitre_technique_id")
                    for finding in (rule_findings + ai_single_findings + ai_correlated_findings)
                    if finding.get("mitre_technique_id")
                }
                logger.info("  techniques mapped: %s", ", ".join(sorted(techniques)) or "none")
            except Exception as e:
                logger.warning("  MITRE error (skipping): %s", e)

            # ── Save report ───────────────────────────────────────────────────
            _banner("STEP 7 / 7  —  Save Report & Generate PDF")
            parsed_source_files = sorted(
                source_labels[file_id]
                for file_id in file_events_map
            )
            correlated_source_files = sorted({
                source_labels.get(str(source_id), str(source_id))
                for chain in chains
                for source_id in (getattr(chain, "source_types", None) or [])
            }) or parsed_source_files
            for finding in ai_single_findings:
                finding.setdefault("finding_type", "single")
                finding.setdefault("source_files", parsed_source_files)
            for finding in ai_correlated_findings:
                finding["finding_type"] = "correlated"
                finding.setdefault("source_files", correlated_source_files)

            single_findings, correlated_findings = _merge_rule_and_ai_findings(
                rule_findings,
                ai_single_findings,
                ai_correlated_findings,
            )
            all_findings = single_findings + correlated_findings
            severity_counts = dict(Counter(f.get("severity", "informational") for f in all_findings))
            mitre_techniques = sorted({
                f["mitre_technique_id"]
                for f in all_findings
                if f.get("mitre_technique_id")
            })

            logger.info("  severity breakdown: %s", severity_counts)

            report = await _upsert_report_and_findings(
                db,
                investigation=investigation,
                single_findings=single_findings,
                correlated_findings=correlated_findings,
                severity_counts=severity_counts,
                mitre_techniques=mitre_techniques,
                parsed_source_files=parsed_source_files,
                correlated_source_files=correlated_source_files,
            )
            await db.commit()
            logger.info("  report : saved  id=%s  findings=%d", str(report.id)[:8], len(all_findings))

            # ── PDF ───────────────────────────────────────────────────────────
            findings_result = await db.execute(select(Finding).where(Finding.report_id == report.id))
            all_db_findings = findings_result.scalars().all()

            temp_dir = os.path.join(settings.LOCAL_STORAGE_PATH, "temp", str(investigation.id))
            os.makedirs(temp_dir, exist_ok=True)

            try:
                from app.reports.pdf_generator import generate_pdf
                from app.reports.uploader import upload_report
                pdf_path = generate_pdf(report, all_db_findings, temp_dir)
                pdf_key = await upload_report(pdf_path, investigation.id, storage)
                report.pdf_storage_key = pdf_key
                await db.commit()
                logger.info("  pdf    : saved → %s", pdf_key)
            except Exception as pdf_exc:
                logger.error("  pdf    : FAILED (pipeline continues): %s", pdf_exc)

            # ── Done ──────────────────────────────────────────────────────────
            investigation.status = "complete"
            investigation.progress_stage = "complete"
            investigation.completed_at = datetime.utcnow()
            await db.commit()

            try:
                from app.services.notification_service import send_job_complete

                if user:
                    send_job_complete(
                        user_email=user.email,
                        investigation_name=investigation.name,
                        report_id=str(report.id),
                        finding_count=len(all_findings),
                    )
            except Exception as notify_exc:
                logger.warning("notification (complete): %s", notify_exc)

            logger.info("")
            logger.info("╔══════════════════════════════════════════════════════╗")
            logger.info("║  ✓  COMPLETE  —  %d findings  —  %s  ║",
                len(all_findings), str(investigation.id)[:8])
            logger.info("╚══════════════════════════════════════════════════════╝")
            logger.info("")

        except Exception as exc:
            try:
                await db.rollback()
            except Exception:
                logger.exception("Pipeline rollback failed for %s", investigation_id)
            logger.error("")
            logger.error("╔══════════════════════════════════════════════════════╗")
            logger.error("║  ✗  PIPELINE FAILED  —  %s", investigation_id[:8])
            logger.error("╚══════════════════════════════════════════════════════╝")
            logger.error("%s", traceback.format_exc())
            try:
                result = await db.execute(
                    select(Investigation).where(Investigation.id == investigation_id)
                )
                investigation = result.scalar_one_or_none()
                if investigation:
                    investigation.status = "failed"
                    investigation.error_message = str(exc)[:500]
                    # Keep last committed stage for UI; default so API never emits an unknown stage
                    if investigation.progress_stage is None:
                        investigation.progress_stage = "queued"
                    await db.commit()
                    try:
                        from app.services.notification_service import send_job_failed

                        ur = await db.execute(
                            select(User).where(User.id == investigation.user_id)
                        )
                        u = ur.scalar_one_or_none()
                        send_job_failed(
                            user_email=u.email if u else "unknown",
                            investigation_name=investigation.name,
                            error_message=str(exc),
                        )
                    except Exception as notify_exc:
                        logger.warning("notification (failed): %s", notify_exc)
            except Exception:
                pass
            raise


# Celery CLI (`celery -A app.tasks.process_investigation`) looks for `app` by default.
app = celery_app


async def run_investigation_pipeline_inline(investigation_id: str, *, cloud_ai_consent: bool = False) -> None:
    """
    Execute the full pipeline in the current event loop (FastAPI background task).
    Used when USE_ASYNCIO_INVESTIGATION_PIPELINE is enabled instead of Celery.
    """
    try:
        await _run_pipeline_guarded(
            investigation_id,
            cloud_ai_consent=cloud_ai_consent,
        )
    except Exception:
        logger.exception("Investigation pipeline failed (inline): %s", investigation_id)


async def recover_orphaned_investigations() -> int:
    """
    Reset investigations left in a running state when the API process restarted.

    When the in-process asyncio pipeline is used, the analysis task lives inside
    the API process, so any restart (e.g. uvicorn --reload) kills in-flight jobs
    and leaves their rows stuck at 'queued'/'processing' forever. Mark those as
    'failed' so the UI unsticks and the user can re-run analysis.

    Only call this in in-process pipeline mode — Celery worker jobs survive API
    restarts and must not be touched.
    """
    from sqlalchemy import update
    from app.dependencies import AsyncSessionLocal
    from app.models.investigation import Investigation

    message = (
        "Analysis was interrupted by a server restart before it finished. "
        "Click Analyze to run it again."
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Investigation)
            .where(Investigation.status.in_(["queued", "processing"]))
            .values(status="failed", progress_stage="failed", error_message=message)
        )
        await db.commit()
        return result.rowcount or 0
