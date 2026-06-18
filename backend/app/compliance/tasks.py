# LogRaven — Compliance Audit Task (multi-framework)
#
# Celery task that orchestrates the full compliance audit pipeline:
#   1. Load AuditJob from DB
#   2. Get AWS session via STS AssumeRole
#   3. Collect raw evidence (CloudTrail, IAM, GuardDuty) + deep collectors
#   4. Sanitize evidence (strip PII) and build normalized signals
#   5. Grade each selected framework via AI (collect once, map to many)
#   6. Persist per-framework results + immutable posture snapshots
#   7. Generate per-framework PDF reports
#   8. Return summary

import asyncio
import traceback
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select

from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="compliance.run_soc2_audit")
def run_soc2_audit(self, audit_job_id: str) -> dict:
    """
    Orchestrate the full compliance audit pipeline for an AuditJob.

    The task name is kept as "compliance.run_soc2_audit" for backward
    compatibility; it now grades every framework selected on the job.
    """
    return asyncio.run(_run_audit_pipeline(self, audit_job_id))


# Generic alias for clarity in new code paths.
run_compliance_audit = run_soc2_audit


@celery_app.task(name="compliance.rescan_due_audits")
def rescan_due_audits() -> dict:
    """Celery-beat entry point: re-run audits whose continuous-monitoring schedule is due."""
    return asyncio.run(_rescan_due())


def _compute_next_run(recurrence: str, now: datetime | None = None) -> datetime | None:
    now = now or datetime.now(timezone.utc)
    if recurrence == "daily":
        return now + timedelta(days=1)
    if recurrence == "weekly":
        return now + timedelta(days=7)
    return None


async def _rescan_due() -> dict:
    """Find recurring audits that are due and re-enqueue them (drift is detected per run)."""
    from app.dependencies import AsyncSessionLocal
    from app.models.soc2_audit import AuditJob

    now = datetime.now(timezone.utc)
    triggered: list[str] = []
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(AuditJob).where(
                AuditJob.recurrence != "none",
                AuditJob.next_run_at.isnot(None),
                AuditJob.next_run_at <= now,
                AuditJob.status.in_(["complete", "failed"]),
            )
        )
        due = list(res.scalars().all())
        for job in due:
            # Push next_run forward immediately so we don't double-trigger.
            job.next_run_at = _compute_next_run(job.recurrence, now)
            job.status = "pending"
            triggered.append(str(job.id))
        await db.commit()

    for job_id in triggered:
        run_soc2_audit.apply_async(args=[job_id], task_id=job_id)
    if triggered:
        logger.info("Continuous monitoring re-enqueued %d audit(s)", len(triggered))
    return {"triggered": triggered, "count": len(triggered)}


def _resolve_frameworks(raw_frameworks) -> list[str]:
    """Validate the job's selected frameworks against the registry; default to soc2."""
    from app.compliance.frameworks import DEFAULT_FRAMEWORK, is_registered

    if not raw_frameworks or not isinstance(raw_frameworks, list):
        return [DEFAULT_FRAMEWORK]
    valid = [fid for fid in raw_frameworks if isinstance(fid, str) and is_registered(fid)]
    return valid or [DEFAULT_FRAMEWORK]


async def _run_audit_pipeline(task_self, audit_job_id: str) -> dict:
    """Async orchestration of all compliance steps."""
    from app.dependencies import AsyncSessionLocal
    from app.models.soc2_audit import AuditJob, AuditResult, ComplianceSnapshot
    from app.compliance.aws_collector import (
        get_aws_session,
        get_cloudtrail_events,
        get_iam_summary,
        get_guardduty_findings,
        AWSConnectionError,
    )
    from app.compliance.collectors import collect_extended_evidence
    from app.compliance.sanitizer import sanitize_for_ai
    from app.compliance.signals import build_evidence_signals
    from app.compliance.frameworks import get_framework
    from app.compliance import ai_grader

    async with AsyncSessionLocal() as db:
        audit_job = None
        try:
            job_uuid = UUID(audit_job_id)

            # ── Step 1: Load AuditJob ───────────────────────────────────────
            logger.info("Step 1: Loading AuditJob %s", audit_job_id)
            result = await db.execute(select(AuditJob).where(AuditJob.id == job_uuid))
            audit_job = result.scalar_one_or_none()
            if audit_job is None:
                error_msg = f"AuditJob {audit_job_id} not found"
                logger.error(error_msg)
                return {"status": "failed", "error": error_msg}

            frameworks = _resolve_frameworks(audit_job.frameworks)
            audit_job.status = "running"
            await db.commit()
            logger.info("  company: %s", audit_job.company_name)
            logger.info("  frameworks: %s", ", ".join(frameworks))
            logger.info("  audit period: %s to %s", audit_job.audit_start_date, audit_job.audit_end_date)

            # ── Step 2: Assume AWS role ─────────────────────────────────────
            logger.info("Step 2: Assuming AWS role")
            try:
                session = get_aws_session(audit_job.role_arn)
                logger.info("  AWS session obtained")
            except AWSConnectionError as e:
                return await _fail(db, audit_job, f"Failed to assume AWS role: {e}")

            # ── Step 3: Collect evidence (base + deep) ──────────────────────
            logger.info("Step 3: Collecting AWS evidence...")
            try:
                cloudtrail_events = get_cloudtrail_events(
                    session, audit_job.audit_start_date, audit_job.audit_end_date
                )
                iam_summary = get_iam_summary(session)
                guardduty_findings = get_guardduty_findings(session)
                extended_evidence = collect_extended_evidence(session)

                audit_job.raw_evidence = {
                    "cloudtrail_events": cloudtrail_events,
                    "iam_summary": iam_summary,
                    "guardduty_findings": guardduty_findings,
                    "extended": extended_evidence,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.commit()
                logger.info("  Raw evidence persisted")
            except Exception as e:  # noqa: BLE001
                logger.error(traceback.format_exc())
                return await _fail(db, audit_job, f"Error collecting AWS evidence: {e}")

            task_self.update_state(state="PROGRESS", meta={"step": "collecting", "percent": 25})

            # ── Step 4: Sanitize + build signals ────────────────────────────
            logger.info("Step 4: Sanitizing evidence and building signals...")
            try:
                sanitized_evidence = sanitize_for_ai(
                    cloudtrail_events, iam_summary, guardduty_findings, extended=extended_evidence
                )
                signals = build_evidence_signals(sanitized_evidence)
                audit_job.sanitized_evidence = {
                    **sanitized_evidence,
                    "sanitized_at": datetime.now(timezone.utc).isoformat(),
                }
                audit_job.evidence_signals = signals
                await db.commit()
                logger.info("  Evidence sanitized; %d signals derived", len(signals))
            except Exception as e:  # noqa: BLE001
                logger.error(traceback.format_exc())
                return await _fail(db, audit_job, f"Error sanitizing evidence: {e}")

            task_self.update_state(state="PROGRESS", meta={"step": "sanitizing", "percent": 45})

            # ── Step 5 + 6: Grade each framework, persist results + snapshots ─
            # Replace any prior results for this job (supports continuous re-scans).
            await db.execute(delete(AuditResult).where(AuditResult.audit_job_id == job_uuid))

            per_framework: dict[str, dict] = {}
            total_frameworks = len(frameworks)
            for idx, framework_id in enumerate(frameworks):
                framework = get_framework(framework_id)
                logger.info("Step 5: Grading %s (%d/%d)...", framework_id, idx + 1, total_frameworks)
                try:
                    control_results = await ai_grader.grade_framework(framework, signals)
                except Exception as e:  # noqa: BLE001
                    logger.error(traceback.format_exc())
                    return await _fail(db, audit_job, f"Error grading {framework_id}: {e}")

                rows = []
                for control in control_results:
                    rows.append(
                        AuditResult(
                            audit_job_id=job_uuid,
                            framework=framework_id,
                            control_id=control.get("control_id", ""),
                            control_name=control.get("control_name", ""),
                            status=control.get("status", "FAIL"),
                            evidence_count=len(control.get("evidence_references", [])),
                            ai_description=control.get("ai_description", ""),
                            raw_evidence_summary={
                                "gaps": control.get("gaps", []),
                                "evidence_references": control.get("evidence_references", []),
                                "confidence": control.get("confidence", "LOW"),
                                "category": control.get("category", ""),
                                "automatable": control.get("automatable", True),
                                "remediation": control.get("remediation", ""),
                            },
                        )
                    )
                db.add_all(rows)

                score_info = ai_grader.score_results(control_results, total=len(framework.controls))
                per_framework[framework_id] = score_info

                # Immutable snapshot + drift vs the previous snapshot for this job/framework.
                prev = await db.execute(
                    select(ComplianceSnapshot)
                    .where(
                        ComplianceSnapshot.audit_job_id == job_uuid,
                        ComplianceSnapshot.framework == framework_id,
                    )
                    .order_by(ComplianceSnapshot.created_at.desc())
                    .limit(1)
                )
                prev_snapshot = prev.scalar_one_or_none()
                delta = None
                if prev_snapshot is not None:
                    delta = round(score_info["score_percent"] - prev_snapshot.score_percent, 2)

                db.add(
                    ComplianceSnapshot(
                        audit_job_id=job_uuid,
                        framework=framework_id,
                        score_percent=score_info["score_percent"],
                        pass_count=score_info["pass_count"],
                        fail_count=score_info["fail_count"],
                        partial_count=score_info["partial_count"],
                        score_delta=delta,
                        evidence_signals=signals,
                        results=control_results,
                    )
                )
                if delta is not None and delta < 0:
                    logger.warning(
                        "  Posture regression for %s: %.1f%% (%+.1f pts)",
                        framework_id, score_info["score_percent"], delta,
                    )

            await db.flush()
            task_self.update_state(state="PROGRESS", meta={"step": "grading", "percent": 80})

            # ── Step 7: Generate per-framework PDFs ─────────────────────────
            logger.info("Step 7: Generating PDF reports...")
            await _generate_reports(db, audit_job, frameworks)

            audit_job.status = "complete"
            audit_job.error_message = None
            if audit_job.recurrence and audit_job.recurrence != "none":
                audit_job.next_run_at = _compute_next_run(audit_job.recurrence)
            await db.commit()
            task_self.update_state(state="PROGRESS", meta={"step": "complete", "percent": 100})

            # ── Step 8: Summary ─────────────────────────────────────────────
            summary = {
                "audit_job_id": str(job_uuid),
                "status": "complete",
                "frameworks": frameworks,
                "scores": per_framework,
            }
            logger.info("Audit complete: %s", summary)
            return summary

        except Exception as e:  # noqa: BLE001
            logger.error(traceback.format_exc())
            if audit_job is not None:
                try:
                    audit_job.status = "failed"
                    audit_job.error_message = f"Unexpected error in audit pipeline: {e}"
                    await db.commit()
                except Exception:  # noqa: BLE001
                    pass
            return {"status": "failed", "error": str(e)}


async def _fail(db, audit_job, message: str) -> dict:
    logger.error(message)
    audit_job.status = "failed"
    audit_job.error_message = message
    await db.commit()
    return {"status": "failed", "error": message}


async def _generate_reports(db, audit_job, frameworks: list[str]) -> None:
    """Generate and cache a PDF per framework. Non-fatal: download route can regenerate."""
    from app.models.soc2_audit import AuditResult
    from app.compliance.report_generator import generate_compliance_report
    from app.compliance.frameworks import get_framework
    from app.utils.storage import create_storage_backend
    from pathlib import Path

    storage = create_storage_backend()
    report_keys: dict[str, str] = {}
    loop = asyncio.get_event_loop()

    for framework_id in frameworks:
        try:
            res = await db.execute(
                select(AuditResult).where(
                    AuditResult.audit_job_id == audit_job.id,
                    AuditResult.framework == framework_id,
                )
            )
            results = list(res.scalars().all())
            framework = get_framework(framework_id)
            pdf_local = await loop.run_in_executor(
                None, generate_compliance_report, audit_job, results, framework.name, framework_id
            )
            pdf_bytes = Path(pdf_local).read_bytes()
            storage_key = f"compliance_reports/{audit_job.id}/{framework_id}.pdf"
            await storage.save_file_from_bytes(storage_key, pdf_bytes)
            report_keys[framework_id] = storage_key
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF generation failed for %s (will regenerate on download): %s", framework_id, exc)

    audit_job.report_keys = report_keys
    # Keep the legacy single-key field pointed at the first framework for compatibility.
    if frameworks and frameworks[0] in report_keys:
        audit_job.pdf_storage_key = report_keys[frameworks[0]]


# Celery CLI: celery -A app.compliance.tasks worker --loglevel=info
app = celery_app
