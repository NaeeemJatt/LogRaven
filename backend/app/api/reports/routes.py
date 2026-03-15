# LogRaven — Report Routes
#
# PURPOSE:
#   HTTP route handlers for fetching and downloading reports.
#
# ENDPOINTS:
#   GET /api/v1/reports/{report_id}          — full report JSON with all findings
#   GET /api/v1/reports/{report_id}/download — returns URL for PDF download
#
# PDF DOWNLOAD NOTE:
#   In development: returns http://localhost:8000/files/reports/{inv_id}/lograven-report-{uuid}.pdf
#   In production: returns a signed S3 URL valid for 24 hours
#
# TODO Month 4 Week 1: Implement this file.

from fastapi import APIRouter

router = APIRouter()
