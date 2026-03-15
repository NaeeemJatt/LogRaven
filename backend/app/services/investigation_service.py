# LogRaven — Investigation Service
#
# PURPOSE:
#   Business logic for investigation management and file upload.
#
# FUNCTIONS:
#   create_investigation(name, user, db) -> Investigation
#   get_investigation(id, user, db) -> Investigation (raise 404 if not found, 403 if not owner)
#   list_investigations(user, db, page, limit) -> (List[Investigation], total)
#   add_file(investigation_id, file, source_type, user, db, storage) -> InvestigationFile
#     - Stream file to storage (never load into memory)
#     - Storage key: uploads/{investigation_id}/{uuid}_{filename}
#     - Create InvestigationFile record with status=pending
#   remove_file(investigation_id, file_id, user, db) -> None
#     - Only allowed when investigation status=draft
#   start_analysis(investigation_id, user, db) -> str (job_id)
#     - Validate at least 1 file uploaded
#     - Set investigation status=queued
#     - Enqueue Celery task: process_investigation.delay(investigation_id)
#     - Return investigation_id as job_id
#
# TODO Month 1 Week 3: Implement this file.
