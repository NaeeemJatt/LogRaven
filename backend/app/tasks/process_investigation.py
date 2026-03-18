# LogRaven — Main Investigation Processing Task

import asyncio
import traceback
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


async def _run_pipeline(investigation_id: str) -> None:
    # Imports deferred to avoid circular imports at module load time
    from app.dependencies import AsyncSessionLocal
    from app.models.investigation import Investigation
    from app.models.investigation_file import InvestigationFile
    from app.parsers import detector
    from app.parsers.windows_event import WindowsEventParser
    from app.parsers.syslog import SyslogParser
    from app.parsers.cloudtrail import CloudTrailParser
    from app.parsers.nginx import NginxParser
    from app.utils.storage import LocalStorageBackend
    from app.config import settings

    storage = LocalStorageBackend(base_path=settings.LOCAL_STORAGE_PATH)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch investigation with all files eagerly
            result = await db.execute(
                select(Investigation)
                .options(selectinload(Investigation.files))
                .where(Investigation.id == investigation_id)
            )
            investigation = result.scalar_one_or_none()
            if investigation is None:
                logger.error("LogRaven: investigation %s not found", investigation_id)
                return

            # 2. Mark as processing
            investigation.status = "processing"
            await db.commit()

            all_events = []

            # 3. Parse each file
            for inv_file in investigation.files:
                try:
                    file_path = await storage.get_file_path(inv_file.storage_key)
                    file_path_str = str(file_path)

                    # Detect log type
                    log_type = detector.detect(file_path_str)
                    inv_file.log_type = log_type
                    await db.commit()

                    # Select parser
                    parser_map = {
                        "windows_event": WindowsEventParser,
                        "syslog":        SyslogParser,
                        "cloudtrail":    CloudTrailParser,
                        "nginx":         NginxParser,
                    }
                    parser_cls = parser_map.get(log_type)
                    if parser_cls is None:
                        inv_file.status = "failed"
                        inv_file.error_message = f"No parser for log_type: {log_type}"
                        await db.commit()
                        continue

                    events = parser_cls().parse(file_path_str)

                    # Tag events with the source_type from the DB record
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
                        inv_file.filename,
                        file_exc,
                        traceback.format_exc(),
                    )
                    inv_file.status = "failed"
                    inv_file.error_message = str(file_exc)[:500]
                    await db.commit()

            logger.info(
                "LogRaven: parsed %d total events from %d files",
                len(all_events),
                len(investigation.files),
            )

            # 4. Mark investigation complete
            investigation.status = "complete"
            investigation.completed_at = datetime.utcnow()
            await db.commit()

            logger.info("LogRaven: investigation %s complete", investigation_id)

        except Exception as exc:
            logger.error(
                "LogRaven: pipeline failed for %s: %s\n%s",
                investigation_id,
                exc,
                traceback.format_exc(),
            )
            try:
                # Re-fetch to avoid stale state
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
