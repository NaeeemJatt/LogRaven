# LogRaven — Report Service
#
# PURPOSE:
#   Business logic for fetching reports and generating download URLs.
#
# FUNCTIONS:
#   get_report(report_id, user, db) -> Report
#     - Fetch report (raise 404 if not found)
#     - Verify user owns the associated investigation (raise 403 if not)
#
#   get_download_url(report_id, user, db, storage) -> DownloadResponse
#     - Get report's pdf_storage_key
#     - Return storage.get_download_url(pdf_storage_key)
#     - Local dev: http://localhost:8000/files/reports/{inv_id}/lograven-report-{uuid}.pdf
#     - Production: signed S3 URL valid for 24 hours
#
# TODO Month 4 Week 1: Implement this file.
