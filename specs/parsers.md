# LogRaven — Parsers Specification

## NormalizedEvent (normalizer.py)
All parsers output this standard schema regardless of source format.

Fields:
- timestamp: datetime (UTC ISO 8601, not null)
- source_type: str (which parser produced it)
- hostname: str | None
- username: str | None (normalized: lowercase, strip whitespace)
- source_ip: str | None (normalized: strip whitespace)
- destination_ip: str | None
- event_type: str (auth_success/auth_failure/sudo/process_exec/network/api_call/other)
- event_id: str | None (Windows EventID, CloudTrail eventName, etc.)
- raw_message: str (original log line, truncated to 500 chars)
- flags: List[str] (brute_force_candidate/privilege_escalation_candidate/etc.)
- severity_hint: str (informational/low/medium/high/critical)

## BaseParser (base.py)
Abstract class. All parsers inherit from this.
Required method: parse(file_path: str) -> List[NormalizedEvent]
Shared utility: _stream_lines(file_path) — UTF-8 with latin-1 fallback, yields lines
Shared utility: _safe_parse_timestamp(raw) — tries multiple formats, returns datetime or None
Shared utility: _log_skip(line, reason) — logs skipped lines as DEBUG, never raises

## windows_event.py
Library: from evtx import PyEvtxParser (pip install evtx — pyevtx-rs bindings)
Input: .evtx binary files or Windows Event CSV exports
EventID map:
  4625 -> auth_failure    4624 -> auth_success    4648 -> explicit_credential
  4720 -> account_created 4688 -> process_exec     4698 -> scheduled_task_create
  4702 -> scheduled_task_modify                     4732 -> group_member_add
Brute force flag: 5+ EventID 4625 from same IP within 60 seconds
Lateral movement flag: EventID 4648 targeting multiple different hostnames

## syslog.py
Multi-pattern approach: test 5 regex patterns against first 200 lines, use best match
Pattern 1: RFC3164  — "MMM DD HH:MM:SS hostname process[pid]: message"
Pattern 2: ISO8601  — "YYYY-MM-DDTHH:MM:SS hostname process[pid]: message"
Pattern 3: Custom1  — timestamp with timezone
Pattern 4: Custom2  — systemd journal format
Pattern 5: Minimal  — any line with sshd/sudo/PAM keyword
AI fallback: if no pattern matches >80%, send 50 sample lines to Claude for format detection
Extract: username from PAM/sshd message patterns, source_ip from "from X.X.X.X" patterns
Flags: brute_force (5+ auth_failure same IP/60s), privilege_escalation (sudo), account_modification

## cloudtrail.py
Input: CloudTrail JSON files (Records array or single event JSON)
Load entire JSON (CloudTrail files typically <20MB)
Iterate Records array, normalize each event
Extract: eventTime, eventSource, eventName, sourceIPAddress, userIdentity
Flag sensitive actions: IAM policy changes, security group mods, root usage, access key creation
Flag failed API calls: any event with errorCode field populated

## nginx.py
Combined log format: 'IP - - [datetime] "METHOD /path HTTP/1.1" status bytes "referer" "ua"'
Also handles Apache combined log format (identical structure)
Rate calculation: count requests per IP per 60-second window
Flags: scanning (50+ requests/IP/60s), 4xx_spike (20+ errors/IP), injection_attempt (SQL/path traversal in URL)
