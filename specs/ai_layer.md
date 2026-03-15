# LogRaven — AI Layer Specification

## ai/router.py
Route all AI analysis. Cloud only for v1.
analyze(events_by_source, correlated_chains, user_tier) -> AnalysisResult
  1. Apply cost ceiling via cost_limiter.py
  2. Build separate prompts for correlated chains and single-source events
  3. Call cloud/engine.py
  4. On failure: try openai_engine.py fallback
  5. Return AnalysisResult

## ai/chunker.py
split_events(events, chunk_size=2000, overlap=50) -> List[List[NormalizedEvent]]
  Overlap of 50 events prevents missing cross-chunk patterns.
merge_results(results) -> List[Finding]
  Deduplicate using hash(event_type + source_ip + mitre_technique_id)
  On collision: keep finding with higher confidence score

## ai/cost_limiter.py
enforce_ceiling(events, user_tier) -> List[NormalizedEvent]
  Limits: free=2000, pro=10000, team=50000
  Selection priority: flagged before unflagged, critical before low
  If ceiling hit: log warning, note in report that X events were rule-only

## ai/cloud/engine.py (Claude claude-sonnet-4-6)
Before sending: strip PII from raw_message (replace internal hostnames with [HOST])
Prompt structure: system prompt (SOC analyst persona) + structured events JSON
Output: strict JSON array of finding objects
Retry: 3 attempts with exponential backoff (2s, 4s, 8s)
Log token count per request to cost_tracking table

## ai/cloud/consent.py
verify_consent(user) -> bool
  Cloud AI requires explicit opt-in. Check user settings/tier.
  Raise ConsentNotGrantedError if not granted.

## ai/prompts/base_prompt.py
System prompt defines:
  - Persona: senior SOC analyst, 15 years experience
  - Output format: STRICT JSON array only, no markdown, no commentary
  - Finding schema: {severity, title, description, mitre_technique_id, iocs, remediation}
  - Severity scale: critical/high/medium/low/informational
  - MITRE rule: never hallucinate technique IDs — omit field if unsure
  - Focus: actionable findings, not comprehensive coverage

## ai/prompts/correlation_prompt.py
build_correlation_prompt(chains) -> str
  Each chain includes: entity, entity_type, source_files, events (sorted by timestamp)
  Instruction: "These events share a common entity across multiple log sources.
  Identify the ATT&CK technique explaining ALL of them together.
  Describe the attack timeline in plain English.
  Assign severity based on combined evidence, not individual events."
