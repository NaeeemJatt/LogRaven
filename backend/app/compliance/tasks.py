# LogRaven — SOC 2 Compliance Audit Task
#
# Celery task that orchestrates the full compliance audit pipeline:
#   1. Load AuditJob from DB
#   2. Get AWS session via STS AssumeRole
#   3. Collect raw evidence (CloudTrail, IAM, GuardDuty)
#   4. Sanitize evidence (strip PII)
#   5. Map to SOC 2 controls via Gemini AI
#   6. Save results to PostgreSQL
#   7. Return summary

import asyncio
import traceback
from uuid import UUID

from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="compliance.run_soc2_audit")
def run_soc2_audit(self, audit_job_id: str) -> dict:
    """
    Orchestrate the full SOC 2 compliance audit pipeline.
    
    Args:
        audit_job_id: UUID of the AuditJob to process
        
    Returns:
        dict with audit summary (status, counts, score)
    """
    return asyncio.run(_run_audit_pipeline(self, audit_job_id))


async def _run_audit_pipeline(task_self, audit_job_id: str) -> dict:
    """Async orchestration of all compliance steps."""
    from datetime import datetime
    from app.dependencies import AsyncSessionLocal
    from app.models.soc2_audit import AuditJob, AuditResult
    from app.compliance.aws_collector import (
        get_aws_session,
        get_cloudtrail_events,
        get_iam_summary,
        get_guardduty_findings,
        AWSConnectionError,
    )
    from app.compliance.sanitizer import sanitize_for_ai
    from app.compliance.soc2_mapper import map_to_soc2_controls, get_overall_compliance_score

    async with AsyncSessionLocal() as db:
        audit_job = None  # guard against UnboundLocalError in outer except
        try:
            job_uuid = UUID(audit_job_id)

            # ═══════════════════════════════════════════════════════════════════════
            # Step 1: Load AuditJob
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 1: Loading AuditJob %s", audit_job_id)
            result = await db.execute(
                select(AuditJob).where(AuditJob.id == job_uuid)
            )
            audit_job = result.scalar_one_or_none()

            if audit_job is None:
                error_msg = f"AuditJob {audit_job_id} not found"
                logger.error(error_msg)
                return {"status": "failed", "error": error_msg}

            # Update status to running
            audit_job.status = "running"
            await db.commit()
            logger.info("  company: %s", audit_job.company_name)
            logger.info("  audit period: %s to %s", audit_job.audit_start_date, audit_job.audit_end_date)

            # ═══════════════════════════════════════════════════════════════════════
            # Step 2: Get AWS session via STS AssumeRole
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 2: Assuming AWS role %s", audit_job.role_arn)
            try:
                session = get_aws_session(audit_job.role_arn)
                logger.info("  ✓ AWS session obtained")
            except AWSConnectionError as e:
                error_msg = f"Failed to assume AWS role: {str(e)}"
                logger.error(error_msg)
                audit_job.status = "failed"
                audit_job.error_message = error_msg
                await db.commit()
                return {"status": "failed", "error": error_msg}

            # ═══════════════════════════════════════════════════════════════════════
            # Step 3: Collect raw evidence
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 3: Collecting AWS evidence...")
            try:
                cloudtrail_events = get_cloudtrail_events(
                    session,
                    audit_job.audit_start_date,
                    audit_job.audit_end_date,
                )
                logger.info("  ✓ CloudTrail events: %d", len(cloudtrail_events.get("Events", [])))

                iam_summary = get_iam_summary(session)
                logger.info("  ✓ IAM summary fetched")

                guardduty_findings = get_guardduty_findings(session)
                logger.info("  ✓ GuardDuty findings: %d", guardduty_findings.get("total_findings", 0))

                # Store raw evidence in AuditJob
                audit_job.raw_evidence = {
                    "cloudtrail_events": cloudtrail_events,
                    "iam_summary": iam_summary,
                    "guardduty_findings": guardduty_findings,
                    "collected_at": datetime.utcnow().isoformat(),
                }
                await db.commit()
                logger.info("  ✓ Raw evidence persisted to AuditJob")

            except Exception as e:
                error_msg = f"Error collecting AWS evidence: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                audit_job.status = "failed"
                audit_job.error_message = error_msg
                await db.commit()
                return {"status": "failed", "error": error_msg}

            # Update progress
            task_self.update_state(
                state="PROGRESS",
                meta={"step": "collecting", "percent": 30},
            )

            # ═══════════════════════════════════════════════════════════════════════
            # Step 4: Sanitize evidence (strip PII)
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 4: Sanitizing evidence for AI...")
            try:
                sanitized_evidence = sanitize_for_ai(
                    cloudtrail_events,
                    iam_summary,
                    guardduty_findings,
                )
                logger.info("  ✓ Evidence sanitized (no PII)")

                # Store sanitized evidence in AuditJob
                audit_job.sanitized_evidence = {
                    **sanitized_evidence,
                    "sanitized_at": datetime.utcnow().isoformat(),
                }
                await db.commit()
                logger.info("  ✓ Sanitized evidence persisted to AuditJob")

            except Exception as e:
                error_msg = f"Error sanitizing evidence: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                audit_job.status = "failed"
                audit_job.error_message = error_msg
                await db.commit()
                return {"status": "failed", "error": error_msg}

            # Update progress
            task_self.update_state(
                state="PROGRESS",
                meta={"step": "sanitizing", "percent": 50},
            )

            # ═══════════════════════════════════════════════════════════════════════
            # Step 5: Map to SOC 2 controls via Gemini AI
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 5: Mapping to SOC 2 controls via Gemini...")
            try:
                control_results = await map_to_soc2_controls(sanitized_evidence)
                logger.info("  ✓ AI mapping complete: %d controls assessed", len(control_results))
                logger.debug("  Control results: %s", [c.get("control_id") for c in control_results])

            except Exception as e:
                error_msg = f"Error mapping to SOC 2 controls: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                audit_job.status = "failed"
                audit_job.error_message = error_msg
                await db.commit()
                return {"status": "failed", "error": error_msg}

            # Update progress
            task_self.update_state(
                state="PROGRESS",
                meta={"step": "mapping", "percent": 75},
            )

            # ═══════════════════════════════════════════════════════════════════════
            # Step 6: Save results to PostgreSQL (bulk insert)
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 6: Saving results to database...")
            try:
                audit_results = []
                for control_data in control_results:
                    audit_result = AuditResult(
                        audit_job_id=job_uuid,
                        control_id=control_data.get("control_id", ""),
                        control_name=control_data.get("control_name", ""),
                        status=control_data.get("status", "FAIL"),
                        evidence_count=len(control_data.get("evidence_references", [])),
                        ai_description=control_data.get("ai_description", ""),
                        raw_evidence_summary={
                            "gaps": control_data.get("gaps", []),
                            "evidence_references": control_data.get("evidence_references", []),
                            "confidence": control_data.get("confidence", "LOW"),
                        },
                    )
                    audit_results.append(audit_result)

                # Bulk add all results
                db.add_all(audit_results)
                await db.flush()
                logger.info("  ✓ Bulk inserted %d AuditResult rows", len(audit_results))

                # Mark job as complete and calculate score
                score_info = get_overall_compliance_score(control_results)
                audit_job.status = "complete"
                await db.commit()
                logger.info("  ✓ AuditJob marked complete")
                logger.info("  ✓ Compliance score: %.1f%%", score_info["score_percent"])

            except Exception as e:
                error_msg = f"Error saving results: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                audit_job.status = "failed"
                audit_job.error_message = error_msg
                await db.commit()
                return {"status": "failed", "error": error_msg}

            # Update progress
            task_self.update_state(
                state="PROGRESS",
                meta={"step": "saving", "percent": 90},
            )

            # ═══════════════════════════════════════════════════════════════════════
            # Step 7: Generate and cache the SOC 2 PDF report
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 7: Generating SOC 2 PDF report...")
            try:
                from pathlib import Path as _Path
                from app.compliance.report_generator import generate_soc2_report
                from app.utils.storage import create_storage_backend
                import asyncio as _asyncio

                storage = create_storage_backend()
                loop = _asyncio.get_event_loop()
                pdf_local_path = await loop.run_in_executor(
                    None, generate_soc2_report, audit_job, audit_results
                )
                pdf_bytes = _Path(pdf_local_path).read_bytes()
                storage_key = f"soc2_reports/{str(job_uuid)}.pdf"
                await storage.save_file_from_bytes(storage_key, pdf_bytes)
                audit_job.pdf_storage_key = storage_key
                await db.commit()
                logger.info("  ✓ PDF uploaded to storage: %s", storage_key)
            except Exception as e:
                # Non-fatal: the download route has a fallback to regenerate
                logger.warning("PDF generation failed (will regenerate on download): %s", str(e))

            task_self.update_state(
                state="PROGRESS",
                meta={"step": "complete", "percent": 100},
            )

            # ═══════════════════════════════════════════════════════════════════════
            # Step 8: Return summary
            # ═══════════════════════════════════════════════════════════════════════
            logger.info("Step 8: Audit complete!")
            summary = {
                "audit_job_id": str(job_uuid),
                "status": "complete",
                "controls_assessed": len(control_results),
                "pass_count": score_info["pass_count"],
                "fail_count": score_info["fail_count"],
                "partial_count": score_info["partial_count"],
                "score_percent": score_info["score_percent"],
            }
            logger.info("  Summary: %s", summary)
            return summary

        except Exception as e:
            # Unhandled exception — set job to failed if we got that far
            error_msg = f"Unexpected error in audit pipeline: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            try:
                if audit_job is not None:
                    audit_job.status = "failed"
                    audit_job.error_message = error_msg
                    await db.commit()
            except Exception:
                pass  # If DB commit fails, just log and continue
            return {"status": "failed", "error": error_msg}


# Celery CLI: celery -A app.compliance.tasks worker --loglevel=info
app = celery_app
