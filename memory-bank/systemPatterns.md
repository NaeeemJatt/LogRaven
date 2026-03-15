# LogRaven — System Patterns

## All Decisions Final
1. Investigation model — named container for 1+ log files
2. Multi-file correlation engine — entity extraction + 5-min window chain building
3. Storage abstraction — LocalStorageBackend dev, S3StorageBackend prod
4. Docker delivery — no hosted SaaS for v1
5. Hardware-bound license keys + PyArmor obfuscation
6. Cloud AI only for v1 — local AI is Phase 2 Enterprise feature
7. Rule engine pre-filter reduces AI event count 60-80%
8. Hard AI cost ceiling per tier: free 2k, pro 10k, team 50k events
9. No admin panel in v1

## LogRaven Data Flow
Create investigation -> upload files with source type tags
-> click Run Analysis -> FastAPI enqueues Celery task
-> Worker: parse all files (pyevtx-rs / multi-pattern / JSON / regex)
-> Rule engine flags events
-> Correlation engine: entity extraction + cross-source chain building
-> Claude AI analysis (cost ceiling enforced)
-> mitreattack-python enriches technique IDs
-> WeasyPrint renders lograven_report.html to PDF
-> lograven-report-{uuid}.pdf saved to local/reports/
-> frontend polling detects complete -> Report page

## Layer Rules
Routes:      HTTP only — validate, call service, return response
Services:    Business logic — no raw DB in routes
Models:      Tables only — no business methods
Parsers:     File parsing only — no DB, no AI calls
Correlation: Event analysis only — no DB writes
AI:          Analysis only — input events, output JSON findings
Storage:     File I/O only — always via StorageBackend abstraction
Tasks:       Pipeline orchestration only — calls other layers
