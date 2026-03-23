# LogRaven — System Patterns

## All Decisions Final
1. Investigation model — named container for 1+ log files
2. Multi-file correlation engine — entity extraction + 5-min window chain building
3. Storage abstraction — LocalStorageBackend dev, S3StorageBackend prod
4. Docker delivery — no hosted SaaS for v1
5. Hardware-bound license keys + PyArmor obfuscation
6. Cloud AI only for v1 — local AI is Phase 2 Enterprise feature
7. Rule engine pre-filter reduces AI event count 60–80%
8. Hard AI cost ceiling per tier: free 2k, pro 10k, team 50k events
9. No admin panel in v1
10. YAML rules primary (2,212 loaded) — hardcoded rules remain as fast fallback
11. PDF: WeasyPrint (Linux/Docker) with xhtml2pdf fallback (Windows dev)

## LogRaven Data Flow
```
Create investigation → upload files with source type tags
→ click Run Analysis → FastAPI enqueues Celery task
→ Worker:
    STEP 1: Fetch investigation + files from DB
    STEP 2: Parse all files (pyevtx-rs / multi-pattern / JSON / regex)
            NormalizedEvent.extra_fields populated by each parser
    STEP 3: Rule engine
            → 4 hardcoded rules (brute force, lateral movement, sensitive action, dedup)
            → YAML evaluator: 2,212 rules via event_id index (fast)
    STEP 4: Correlation engine (2+ files only)
            → entity extraction + cross-source 5-min chain building
    STEP 5: AI cost ceiling enforced (priority-based: critical→high→medium→info)
    STEP 6: Gemini 2.5 Flash analysis
            → analyze_events() per log_type + analyze_chains() for correlated chains
            → 3-attempt exponential backoff
    STEP 7: MITRE ATT&CK enrichment (graceful skip if missing)
    STEP 8: Save Report + Finding rows to DB
    STEP 9: Generate PDF
            → WeasyPrint (primary) → xhtml2pdf (Windows fallback)
            → upload via storage abstraction
    STEP 10: investigation.status = "complete"
→ Frontend polling detects complete → navigates to Report page
```

## Layer Rules
| Layer       | Responsibility                                     | Forbidden                         |
|-------------|----------------------------------------------------|------------------------------------|
| Routes      | HTTP only — validate, call service, return         | Raw DB, business logic             |
| Services    | Business logic                                     | Raw DB in routes                   |
| Models      | Tables only                                        | Business methods                   |
| Parsers     | File parsing only                                  | DB writes, AI calls                |
| Rules       | Event flagging only                                | DB writes, network calls           |
| Correlation | Event analysis only                                | DB writes                          |
| AI          | Input events → output JSON findings                | Side effects                       |
| Storage     | File I/O only                                      | Always via StorageBackend          |
| Tasks       | Pipeline orchestration only                        | Business logic                     |

## Rule Engine Architecture
```
rules/engine.py          ← entry point, called from pipeline
  └── hardcoded rules    ← 4 rules (brute force, lateral, sensitive, dedup)
  └── rules/loader.py    ← loads all YAML from app/data/rules/ (cached)
  └── rules/evaluator.py ← run_yaml_rules()
        ├── _build_index()     builds log_type → event_id → [rules] dict
        ├── simple rules       per-event lookup via index (~10-15 rules per event)
        └── threshold rules    sliding-window aggregate

rules/schema.py          ← Pydantic models for YAML rule format
  ├── SimpleCondition    (field, op, value, values, negate, _compiled_re)
  ├── SimpleMatch        (log_type, conditions, condition_logic)
  ├── ThresholdMatch     (log_type, event_type, group_by, count, window_seconds)
  └── RuleDefinition     (id, title, severity, flag, mitre_*, match)
```

## NormalizedEvent Schema
```python
@dataclass
class NormalizedEvent:
    timestamp:        datetime | None
    source_type:      str            # "windows_endpoint", "syslog", "cloudtrail", "nginx"
    event_type:       str            # "auth_success", "auth_failure", "process_creation", etc.
    event_id:         str | None     # Windows EventID or equivalent
    hostname:         str | None
    username:         str | None
    source_ip:        str | None
    destination_ip:   str | None
    raw_message:      str
    flags:            list           # detection flags appended by rules
    severity_hint:    str            # "informational" / "low" / "medium" / "high" / "critical"
    extra_fields:     dict           # source-specific metadata for YAML rule matching
```

## Error Handling Patterns
- `LogRavenError`: base exception with `status_code = 500`, `message`, `code`
- Subclasses override `status_code` (e.g. `NotFoundError` = 404, `AuthError` = 401)
- HTTP 500 handler returns generic message — never exposes raw exception to client
- Pipeline failures: `investigation.error_message` stores `str(exc)[:500]`
- Rule engine failures: caught and logged — never block the pipeline
- PDF failures: logged as warning — investigation still marked complete
- Gemini failures: 3-attempt backoff, then graceful skip returning empty findings
