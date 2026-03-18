# LogRaven — Main Investigation Processing Task

import asyncio
import traceback
from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="process_investigation", bind=True, max_retries=0)
def process_investigation(self, investigation_id: str):
    """
    LogRaven main processing pipeline.
    Runs synchronously via asyncio.run() because SQLAlchemy sessions are async.
    """
    asyncio.run(_run_pipeline(investigation_id))


async def _run_pipeline(investigation_id: str) -> None:  # noqa: C901
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
    from app.utils.storage import LocalStorageBackend
    from app.config import settings

    storage = LocalStorageBackend(base_path=settings.LOCAL_STORAGE_PATH)

    async with AsyncSessionLocal() as db:
        try:
            # ── Step 1: Fetch investigation with files ────────────────────────
            result = await db.execute(
                select(Investigation)
                .options(selectinload(Investigation.files))
                .where(Investigation.id == investigation_id)
            )
            investigation = result.scalar_one_or_none()
            if investigation is None:
                logger.error("LogRaven: investigation %s not found", investigation_id)
                return

            # ── Step 2: Mark processing ───────────────────────────────────────
            investigation.status = "processing"
            await db.commit()

            all_events = []
            primary_log_type: str | None = None

            # ── Step 3: Parse each file ───────────────────────────────────────
            parser_map = {
                "windows_event": WindowsEventParser,
                "syslog":        SyslogParser,
                "cloudtrail":    CloudTrailParser,
                "nginx":         NginxParser,
            }
            for inv_file in investigation.files:
                try:
                    file_path = await storage.get_file_path(inv_file.storage_key)
                    file_path_str = str(file_path)

                    log_type = detector.detect(file_path_str)
                    inv_file.log_type = log_type
                    await db.commit()

                    if primary_log_type is None:
                        primary_log_type = log_type

                    parser_cls = parser_map.get(log_type)
                    if parser_cls is None:
                        inv_file.status = "failed"
                        inv_file.error_message = f"No parser for log_type: {log_type}"
                        await db.commit()
                        continue

                    events = parser_cls().parse(file_path_str)
                    for ev in events:
                        ev.source_type = inv_file.source_type

                    inv_file.status = "parsed"
                    inv_file.event_count = len(events)
                    inv_file.parsed_at = datetime.utcnow()
                    await db.commit()

                    all_events.extend(events)

                except Exception as file_exc:
                    logger.error(
                        "LogRaven: error parsing file %s: %s\n%s",
                        inv_file.filename, file_exc, traceback.format_exc(),
                    )
                    inv_file.status = "failed"
                    inv_file.error_message = str(file_exc)[:500]
                    await db.commit()

            logger.info(
                "LogRaven: parsed %d total events from %d files",
                len(all_events), len(investigation.files),
            )

            # ── Step 5a: Rule engine ──────────────────────────────────────────
            try:
                from app.rules.engine import run_rules
                all_events = run_rules(all_events)
                logger.info("LogRaven: rule engine complete, %d events after rules", len(all_events))
            except Exception as e:
                logger.warning("LogRaven: rule engine error (continuing): %s", e)

            # ── Step 5b: Correlation engine ───────────────────────────────────
            correlation_summary: dict = {}
            try:
                if len(investigation.files) >= 2:
                    from app.correlation.engine import correlate
                    correlation_summary = correlate(all_events)
                    logger.info(
                        "LogRaven: correlation found %d chains",
                        correlation_summary.get("chain_count", 0),
                    )
            except Exception as e:
                logger.warning("LogRaven: correlation error (continuing): %s", e)

            # ── Step 5c: Cost ceiling ─────────────────────────────────────────
            user_result = await db.execute(
                select(User).where(User.id == investigation.user_id)
            )
            user = user_result.scalar_one_or_none()
            tier = user.tier if user else "free"

            events_for_ai = all_events
            try:
                from app.ai.cost_limiter import enforce_ceiling
                events_for_ai, was_truncated = enforce_ceiling(all_events, tier)
                if was_truncated:
                    logger.info(
                        "LogRaven: cost ceiling hit — sending %d/%d events to AI (tier=%s)",
                        len(events_for_ai), len(all_events), tier,
                    )
                else:
                    logger.info(
                        "LogRaven: %d events sent to AI (tier=%s)", len(events_for_ai), tier,
                    )
            except Exception as e:
                logger.warning("LogRaven: cost limiter error (continuing): %s", e)

            # ── Step 5e–5g: AI analysis ───────────────────────────────────────
            single_findings: list[dict] = []
            correlated_findings: list[dict] = []
            chains = correlation_summary.get("chains", [])

            # Determine log_type for prompt routing
            if len(investigation.files) == 1 and primary_log_type:
                ai_log_type = primary_log_type
            else:
                ai_log_type = "mixed"

            try:
                from app.ai.router import route_analysis
                single_findings, correlated_findings = await route_analysis(
                    events_for_ai, ai_log_type, chains, tier
                )
                logger.info(
                    "LogRaven AI: %d single findings, %d correlated findings",
                    len(single_findings), len(correlated_findings),
                )
            except Exception as e:
                logger.error("LogRaven AI: analysis error (continuing): %s\n%s", e, traceback.format_exc())

            # ── Step 5h: MITRE enrichment ─────────────────────────────────────
            try:
                from app.reports.mitre_mapper import enrich_all
                single_findings = enrich_all(single_findings)
                correlated_findings = enrich_all(correlated_findings)
            except Exception as e:
                logger.warning("LogRaven MITRE: enrichment error (continuing): %s", e)

            # ── Step 5i: Save Report and Findings ─────────────────────────────
            all_findings = single_findings + correlated_findings
            severity_counts = dict(
                Counter(f.get("severity", "informational") for f in all_findings)
            )
            mitre_techniques = list({
                f["mitre_technique_id"]
                for f in all_findings
                if f.get("mitre_technique_id")
            })

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
            await db.flush()  # populate report.id before creating Finding rows

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
            logger.info(
                "LogRaven: saved report %s with %d total findings",
                report.id, len(all_findings),
            )

            # ── Step 5j: Mark complete ────────────────────────────────────────
            investigation.status = "complete"
            investigation.completed_at = datetime.utcnow()
            await db.commit()

            logger.info("LogRaven: investigation %s complete", investigation_id)

        except Exception as exc:
            logger.error(
                "LogRaven: pipeline failed for %s: %s\n%s",
                investigation_id, exc, traceback.format_exc(),
            )
            try:
                result = await db.execute(
                    select(Investigation).where(Investigation.id == investigation_id)
                )
                investigation = result.scalar_one_or_none()
                if investigation:
                    investigation.status = "failed"
                    await db.commit()
            except Exception:
                pass
            raise
