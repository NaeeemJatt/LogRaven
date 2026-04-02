# LogRaven — Main Investigation Processing Task

import asyncio
import os
import traceback
from pathlib import Path
from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger("lograven.pipeline")

_SEP = "─" * 55


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


@celery_app.task(name="process_investigation", bind=True, max_retries=0)
def process_investigation(self, investigation_id: str, cloud_ai_consent: bool = False):
    asyncio.run(_run_pipeline(investigation_id, cloud_ai_consent=cloud_ai_consent))


async def _run_pipeline(investigation_id: str, *, cloud_ai_consent: bool = False) -> None:  # noqa: C901
    from app.dependencies import AsyncSessionLocal
    from app.models.finding import Finding
    from app.models.investigation import Investigation
    from app.models.report import Report
    from app.models.user import User
    from app.parsers import detector
    from app.parsers.cloudtrail import CloudTrailParser
    from app.parsers.nginx import NginxParser
    from app.parsers.syslog import SyslogParser
    from app.parsers.windows_event import WindowsEventParser
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

            logger.info("  name  : %s", investigation.name)
            logger.info("  files : %d", len(investigation.files))

            from app.ai.cloud.consent import require_cloud_ai_consent

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
            file_events_map: dict[str, list] = {}   # keyed by filename for correlation

            # ── Step 3: Parse files ───────────────────────────────────────────
            _banner("STEP 2 / 7  —  Parse Log Files")
            parser_map = {
                "windows_event": WindowsEventParser,
                "syslog":        SyslogParser,
                "cloudtrail":    CloudTrailParser,
                "nginx":         NginxParser,
                "iis":           NginxParser,   # NginxParser handles IIS W3C internally
            }

            for inv_file in investigation.files:
                logger.info("  file  : %s", inv_file.filename)
                try:
                    file_path = await storage.get_file_path(inv_file.storage_key)
                    file_path_str = str(file_path)
                    try:
                        log_type = detector.detect(file_path_str)
                        inv_file.log_type = log_type
                        await db.commit()
                        logger.info("  type  : %s  →  detected as [%s]", inv_file.filename, log_type)

                        if primary_log_type is None:
                            primary_log_type = log_type

                        parser_cls = parser_map.get(log_type)
                        if parser_cls is None:
                            logger.warning("  SKIP  : no parser for log_type=%s", log_type)
                            inv_file.status = "failed"
                            inv_file.error_message = f"No parser for log_type: {log_type}"
                            await db.commit()
                            continue

                        events = parser_cls().parse(file_path_str)
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

                        for ev in events:
                            ev.source_type = inv_file.source_type

                        inv_file.status = "parsed"
                        inv_file.event_count = len(events)
                        inv_file.parsed_at = datetime.utcnow()
                        await db.commit()
                        logger.info("  parsed: %d events from %s", len(events), inv_file.filename)
                        all_events.extend(events)
                        file_events_map[inv_file.filename] = events
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
            try:
                from app.rules.engine import run_rules
                before = len(all_events)
                all_events = run_rules(all_events)
                flagged = sum(1 for e in all_events if e.flags)
                logger.info("  events : %d in → %d out", before, len(all_events))
                logger.info("  flagged: %d events have detection flags", flagged)
            except Exception as e:
                logger.warning("  rule engine error (skipping): %s", e)

            await _commit_progress(db, investigation, "correlation")

            # ── Step 5: Correlation ───────────────────────────────────────────
            _banner("STEP 4 / 7  —  Correlation Engine")
            correlation_summary: list = []
            try:
                if len(file_events_map) >= 2:
                    from app.correlation.engine import correlate
                    correlation_summary = correlate(
                        str(investigation.id), file_events_map
                    )
                    chains_count = len(correlation_summary) if isinstance(correlation_summary, list) else 0
                    logger.info("  chains : %d cross-source chains found", chains_count)
                else:
                    logger.info("  skipped (only 1 file — need 2+ for correlation)")
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
            _banner("STEP 5 / 7  —  Gemini AI Analysis")
            single_findings: list[dict] = []
            correlated_findings: list[dict] = []
            chains = correlation_summary if isinstance(correlation_summary, list) else []

            ai_log_type = primary_log_type if (len(investigation.files) == 1 and primary_log_type) else "mixed"
            logger.info("  model  : gemini-2.5-flash")
            logger.info("  type   : %s  |  events: %d  |  chains: %d",
                ai_log_type, len(events_for_ai), len(chains))

            try:
                from app.ai.router import route_analysis

                single_findings, correlated_findings = await route_analysis(
                    events_for_ai, ai_log_type, chains, tier
                )
                logger.info("  single : %d findings", len(single_findings))
                logger.info("  correl : %d findings", len(correlated_findings))
            except Exception as e:
                logger.error("  AI error (continuing): %s", e, exc_info=True)

            await _commit_progress(db, investigation, "building_report")

            # ── MITRE enrichment ──────────────────────────────────────────────
            _banner("STEP 6 / 7  —  MITRE ATT&CK Enrichment")
            try:
                from app.reports.mitre_mapper import enrich_all
                single_findings      = enrich_all(single_findings)
                correlated_findings  = enrich_all(correlated_findings)
                techniques = {f.get("mitre_technique_id") for f in (single_findings + correlated_findings) if f.get("mitre_technique_id")}
                logger.info("  techniques mapped: %s", ", ".join(sorted(techniques)) or "none")
            except Exception as e:
                logger.warning("  MITRE error (skipping): %s", e)

            # ── Save report ───────────────────────────────────────────────────
            _banner("STEP 7 / 7  —  Save Report & Generate PDF")
            all_findings = single_findings + correlated_findings
            severity_counts = dict(Counter(f.get("severity", "informational") for f in all_findings))
            mitre_techniques = list({f["mitre_technique_id"] for f in all_findings if f.get("mitre_technique_id")})

            logger.info("  severity breakdown: %s", severity_counts)

            report = Report(
                investigation_id=investigation.id,
                user_id=investigation.user_id,
                summary=(
                    f"Analysis complete. Found {len(single_findings)} individual findings "
                    f"and {len(correlated_findings)} correlated findings."
                ),
                severity_counts=severity_counts,
                correlated_findings=correlated_findings,
                single_source_findings=single_findings,
                mitre_techniques=mitre_techniques,
            )
            db.add(report)
            await db.flush()

            for finding_dict in single_findings:
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
                    finding_type="single",
                    confidence=float(finding_dict.get("confidence", 0.8)),
                    source_files=[],
                ))

            for finding_dict in correlated_findings:
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
                    finding_type="correlated",
                    confidence=float(finding_dict.get("confidence", 0.8)),
                    source_files=[],
                ))

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
