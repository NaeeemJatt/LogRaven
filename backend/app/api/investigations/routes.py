# LogRaven — Investigation Routes
#
# PURPOSE:
#   HTTP route handlers for investigation CRUD and file upload.
#   All business logic lives in services/investigation_service.py.
#
# ENDPOINTS:
#   POST   /api/v1/investigations                        — create investigation
#   GET    /api/v1/investigations                        — list user investigations
#   GET    /api/v1/investigations/{id}                   — get investigation detail
#   POST   /api/v1/investigations/{id}/files             — upload file with source_type
#   DELETE /api/v1/investigations/{id}/files/{file_id}   — remove file
#   POST   /api/v1/investigations/{id}/analyze           — start LogRaven analysis
#   GET    /api/v1/investigations/{id}/status            — poll job progress
#
# FILE UPLOAD NOTE:
#   Files must stream to LocalStorageBackend — never load into memory.
#   Storage key format: uploads/{investigation_id}/{uuid}_{filename}
#
# TODO Month 1 Week 3: Implement this file.

from fastapi import APIRouter

router = APIRouter()

# TODO: Implement all investigation endpoints
