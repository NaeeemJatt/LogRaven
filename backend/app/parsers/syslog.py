# LogRaven — Linux Syslog / auth.log Parser
#
# PURPOSE:
#   Parses Linux auth.log, /var/log/secure, and general syslog files.
#   Handles the major syslog format variations across Linux distributions.
#
# MULTI-PATTERN APPROACH:
#   Reads first 200 lines. Tests 5 regex patterns. Uses the one matching
#   the highest percentage of lines. This handles Ubuntu/CentOS/Debian
#   differences without breaking on custom formats.
#
# PATTERNS TESTED:
#   1. RFC3164:  "MMM DD HH:MM:SS hostname process[pid]: message"
#   2. ISO8601:  "YYYY-MM-DDTHH:MM:SS+tz hostname process[pid]: message"
#   3. Custom1:  RFC3164 with year
#   4. Custom2:  systemd journal format
#   5. Minimal:  any line containing sshd|sudo|PAM keyword
#
# AI FALLBACK:
#   If no pattern matches >80% of sample lines, send 50 sample lines
#   to Claude with a format detection prompt. AI identifies the format
#   and returns a working regex. This handles truly custom syslog formats.
#
# DETECTION FLAGS:
#   brute_force: 5+ auth_failure from same IP within 60 seconds
#   privilege_escalation: any sudo event
#   account_modification: useradd/passwd/usermod in message
#
# TODO Month 2 Week 1: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class SyslogParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Multi-pattern detection then parse
        # TODO: AI-assisted fallback for unknown formats
        return []
